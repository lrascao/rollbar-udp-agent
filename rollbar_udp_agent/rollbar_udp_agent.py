"""
A Python Rollbar udp agent
"""

import logging
import os
import sys
import optparse
import threading
import signal
import socket
import select
import Queue
import re
import ConfigParser

# 3rd party
import requests
import json

from daemon import Daemon, Supervisor
from util import PidFile

os.umask(022)

# CONSTANTS
UDP_SOCKET_TIMEOUT = 5
VERSION = "1.0.0"
ROLLBARD_FLUSH_INTERVAL = 10   # seconds
DEFAULT_EVENT_CHUNK_SIZE = 2
DEFAULT_EVENT_CHUNK_BYTES = 1024 * 1024 * 2

log = logging.getLogger(__name__)

def init(config):
    """Configure the server and the reporting thread.
    """
    c = config['_global']

    log.debug("Configuring rollbar-udp-agent")

    port = c['listen_port']
    interval = c['flush_interval']
    url = c['rollbar_url']
    event_chunk_size = c.get('event_chunk_size')
    event_chunk_bytes = c.get('event_chunk_bytes')
    api_key = c.get('api_key')
    bulk_report = c.get('bulk_report')

    # Start the reporting thread.
    reporter = Reporter(interval, url, api_key, event_chunk_size, event_chunk_bytes, bulk_report)

    # Start the server on an IPv4 stack
    # Default to loopback
    server_host = c['bind_host']

    server = Server(reporter, server_host, port)

    return reporter, server, c

class rollbard(Daemon):
    """ This class is the rollbar daemon. """

    def __init__(self, pid_file, server, reporter, autorestart):
        Daemon.__init__(self, pid_file, autorestart=autorestart)
        self.server = server
        self.reporter = reporter

    def _handle_sigterm(self, signum, frame):
        log.debug("Caught sigterm. Stopping run loop.")
        self.server.stop()

    def run(self):
        # Gracefully exit on sigterm.
        signal.signal(signal.SIGTERM, self._handle_sigterm)

        # Handle Keyboard Interrupt
        signal.signal(signal.SIGINT, self._handle_sigterm)

        # Start the reporting thread before accepting data
        self.reporter.start()

        try:
            try:
                self.server.start()
            except Exception, e:
                log.exception('Error starting server')
                raise e
        finally:
            # The server will block until it's done. Once we're here, shutdown
            # the reporting thread.
            self.reporter.stop()
            self.reporter.join()
            log.info("rollbard is stopped")
            # Restart if asked to restart
            if self.autorestart:
                sys.exit(Supervisor.RESTART_EXIT_STATUS)

    def info(self):
        return ""

class Reporter(threading.Thread):
    """
    The reporter periodically sends the aggregated errors to the
    server.
    """

    def __init__(self, interval, url, api_key, event_chunk_size, event_chunk_bytes, bulk_report):
        threading.Thread.__init__(self)
        self.finished = threading.Event()
        self.flush_count = 0
        self.interval = interval
        self.queue = Queue.Queue()
        self.event_chunk_size = event_chunk_size
        self.event_chunk_bytes = event_chunk_bytes
        self.n_queued_events = 0
        self.n_queued_bytes = 0
        self.url = url
        self.api_key = api_key
        self.bulk_report = bulk_report

    def dict_replace(self, adict, k, v):
        for key in adict.keys():
            if key == k:
                adict[key] = v
            elif type(adict[key]) is dict:
                self.dict_replace(adict[key], k, v)

    def stop(self):
        log.info("Stopping reporter")
        self.finished.set()

    def run(self):

        while not self.finished.isSet():  # Use camel case isSet for 2.4 support.
            self.finished.wait(self.interval)
            self.flush()

        # Clean up the status messages.
        log.debug("Stopped reporter")

    def submit(self, packets):
        self.queue.put(packets)
        self.n_queued_events += 1
        self.n_queued_bytes += len(packets)
        log.debug("queued events: %d, queued bytes: %d",
            self.n_queued_events, self.n_queued_bytes)
        # if the threshold has been exceeded then package
        # up all the packets and send them to reporter
        if self.n_queued_events >= self.event_chunk_size or \
           self.n_queued_bytes >= self.event_chunk_bytes:
            self.flush()
        return None

    def http_request(self, json_payload):
        headers = {'content-type' : 'application/json',
                   'X-Rollbar-Access-Token' : self.api_key}
        encoded_payload = json.dumps(json_payload)
        log.debug(encoded_payload)
        r = requests.post(self.url, data = encoded_payload, timeout = 5, headers = headers)
        log.debug(r.text)

    def flush(self):
        if self.queue.qsize() == 0:
            return

        bulk_data = []
        while not self.queue.empty():
            data = self.queue.get()
            # parse the data into a json object
            json_data = json.loads(data)
            # either report the error right away or
            # aggregate it in a single bulk report
            if self.bulk_report:
                bulk_data.append(json_data['data'])
            else:
                if self.api_key != None:
                    self.dict_replace(json_data, 'access_token', self.api_key)
                self.http_request(json_data)

        if self.bulk_report:
            payload_data = {'payload' :
                            {'access_token' : self.api_key,
                             'data' : bulk_data}}
            self.http_request(payload_data)

        self.n_queued_events = 0
        self.n_queued_bytes = 0

class Server(object):
    """
    A rollbard udp server.
    """

    def __init__(self, reporter, host, port):
        self.host = host
        self.port = int(port)
        self.address = (self.host, self.port)
        self.reporter = reporter
        self.buffer_size = 1024 * 8

        self.running = False

    def start(self):
        """ Run the server. """
        # Bind to the UDP socket.
        # IPv4 only
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setblocking(0)
        try:
            self.socket.bind(self.address)
        except socket.gaierror:
            if self.address[0] == 'localhost':
                log.warning("Warning localhost seems undefined in your host file, using 127.0.0.1 instead")
                self.address = ('127.0.0.1', self.address[1])
                self.socket.bind(self.address)

        log.info('Listening on host & port: %s' % str(self.address))

        # Inline variables for quick look-up.
        buffer_size = self.buffer_size
        reporter_submit = self.reporter.submit
        sock = [self.socket]
        socket_recv = self.socket.recv
        select_select = select.select
        select_error = select.error
        timeout = UDP_SOCKET_TIMEOUT

        # Run our select loop.
        self.running = True
        while self.running:
            try:
                ready = select_select(sock, [], [], timeout)
                if ready[0]:
                    message = socket_recv(buffer_size)
                    reporter_submit(message)

            except select_error, se:
                # Ignore interrupted system calls from sigterm.
                errno = se[0]
                if errno != 4:
                    raise
            except (KeyboardInterrupt, SystemExit):
                break
            except Exception:
                log.exception('Error receiving datagram')

    def stop(self):
        self.running = False

def parse_config(filename):
    # if the filename containing rollbar agent configuration does not exist, exit
    if not os.path.isfile(filename):
        logging.critical('The config file %s was not found.', filename)
        sys.exit(1)

    defaults = {
        'listen_port': 7521,
        'rollbar_url': 'https://api.rollbar.com/api/1/item/',
        'api_key': '',
        'bind_host': '',
        'event_chunk_size': DEFAULT_EVENT_CHUNK_SIZE,
        'event_chunk_bytes': DEFAULT_EVENT_CHUNK_BYTES,
        'flush_interval' : ROLLBARD_FLUSH_INTERVAL,
        'bulk_report': 'false'
    }

    def to_int(val):
        return int(val)
    def to_list(val):
        return re.split(r'\s+', val)
    def to_dict(val):
        log_level_dict = ast.literal_eval(val)
        return log_level_dict
    def to_bool(val):
        return val.lower() == 'true'
    def as_is(val):
        return val

    parsers = {
        'listen_port': to_int,
        'rollbar_url': as_is,
        'api_key': as_is,
        'bind_host': as_is,
        'event_chunk_size': to_int,
        'event_chunk_bytes': to_int,
        'flush_interval' : to_int,
        'bulk_report': to_bool
    }

    cp = ConfigParser.SafeConfigParser(defaults)
    cp.read([filename])

    config = {'_formats': {}}
    for section_name in cp.sections():
        if section_name.startswith('app:'):
            app_name = section_name[len('app:'):]
            app = {'name': app_name}
            for option_name, raw_value in cp.items(section_name):
                if option_name in parsers:
                    value = parsers[option_name](raw_value)
                else:
                    value = raw_value
                app[option_name] = value

            config[app_name] = app
        elif section_name.startswith('format:'):
            format_name = section_name[len('format:'):]
            format = {'name': format_name}

            format_type = cp.get(section_name, 'type')
            format_spec = cp.get(section_name, 'format', True)
            try:
                format_datefmt = cp.get(section_name, 'datefmt', True)
            except ConfigParser.NoOptionError:
                format_datefmt = DEFAULT_DATEFMT

            if format_type != 'python':
                log.warning("Unrecognized format type: %s", format_type)
                continue
            regex, datefmt = build_python_log_format_parser(format_spec, format_datefmt)
            format['regex'] = regex
            format['datefmt'] = datefmt

            config['_formats'][format_name] = format

    global_config = cp.defaults()
    config['_global'] = {}
    for option_name, raw_value in global_config.iteritems():
        if option_name in parsers:
            value = parsers[option_name](raw_value)
        else:
            value = raw_value
        config['_global'][option_name] = value

    return config

def build_option_parser():
    parser = optparse.OptionParser("%prog [start|stop|restart|status]")

    parser.add_option('-c', '--config', dest='config_file', action='store',
        default='/etc/rollbar-udp-agent.conf', help='Path to configuration file. Default: rollbar-udp-agent.conf in the working directory.')

    # verbosity
    verbosity = optparse.OptionGroup(parser, 'Verbosity')
    verbosity.add_option('-v', '--verbose', dest='verbose', action='store_true', default=False,
        help='Verbose output (uses log level DEBUG)')
    verbosity.add_option('-q', '--quiet', dest='quiet', action='store_true', default=False,
        help='Quiet output (uses log level WARNING)')

    parser.add_option_group(verbosity)

    return parser
