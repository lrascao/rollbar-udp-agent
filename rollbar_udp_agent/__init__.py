from rollbar_udp_agent import *

def main(config_path=None):
    """ The main entry point for rollbar udp agent. """

    # first parse command-line options to get the path to the config file
    parser = build_option_parser()
    (options, args) = parser.parse_args()

    # set up logging
    level = logging.CRITICAL
    if options.verbose:
        level = logging.DEBUG
    elif options.quiet:
        level = logging.WARNING

    formatter = logging.Formatter("%(asctime)s %(levelname)-5.5s %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(level)
    file_handler = logging.FileHandler('/var/log/rollbar-udp-agent.log')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    log.addHandler(stream_handler)
    log.addHandler(file_handler)
    log.setLevel(level)

    log.debug("using config file %s", options.config_file)

    # now parse the config file
    config = parse_config(options.config_file)

    reporter, server, conf = init(config)
    pid_file = PidFile('rollbar-udp-agent')
    daemon = rollbard(pid_file.get_path(), server, reporter, True)

    # If no args were passed in, run the server in the foreground.
    if not args:
        daemon.start(foreground=True)
        return 0

    # Otherwise, we're process the deamon command.
    else:
        command = args[0]

        if command == 'start':
            daemon.start()
        elif command == 'stop':
            daemon.stop()
        elif command == 'restart':
            daemon.restart()
        elif command == 'status':
            daemon.status()
        elif command == 'info':
            return daemon.info()
        else:
            sys.stderr.write("Unknown command: %s\n\n" % command)
            parser.print_help()
            return 1
        return 0
