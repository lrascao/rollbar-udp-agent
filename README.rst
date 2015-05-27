rollbar-udp-agent
=============
A daemon that listens on a udp port and pushes messages to Rollbar.

Requirements
------------
rollbar-udp-agent requires:

- A unix-like system (tested on Fedora Linux and Mac OS X)
- Python 2.6+
- requests 0.13.1+ (will be installed by pip)
- a Rollbar_ account

Installation
------------

**Installing**

Obtain a post_server_item access token from your project's Rollbar settings page and execute

    ROLLBAR_ACCESS_TOKEN=post_server_item_access_token bash -c "$(curl -L https://raw.githubusercontent.com/lrascao/rollbar-udp-agent/master/setup.sh)"

**Installing with pip**

In a virtualenv, install like so::

    sudo pip install rollbar-udp-agent

**init.d script**

rollbar-agent comes with an example init.d script, chkconfig compatible and tested on Fedora Linux, update-rc.d on Ubuntu Linux.

On Ubuntu, you'll need to add to rc.d. Run the following::

    update-rc.d rollbar-udp-agent defaults

On Fedora, add to chkconfig::

    sudo chkconfig --add rollbar-udp-agent
    sudo chkconfig rollbar-udp-agent on

On other systems, check your system's documentation for its equivalent of chkconfig.

Now, start the service::

    sudo service rollbar-udp-agent start

To check that it's running, tail its log file::

    tail -f /var/log/rollbar-udp-agent.log

Configuration
-------------
Configuration options for rollbar-udp-agent itself are in `/etc/rollbar-udp-agent.conf`.

**rollbar-udp-agent.conf**
At the bare minimum, you will want to change the following variables:

- ``api_key`` -- your Rollbar access token, specifically an API token that allows "post_server_item"

The following options are optional and have default values

- ``listen_port`` -- the udp port to listen for messages on (default 7521)
- ``bind_host`` --  interface to listen on (default is all interfaces)
- ``rollbar_url`` -- url to post messages to (default https://api.rollbar.com/api/1/item/)
- ``event_chunk_size`` --  number of events to chunk before sending to rollbar (default 50)
- ``event_chunk_bytes`` -- number of bytes to chunk before sending to rollbar (default 1048576, 1MB)
- ``flush_interval`` -- flush messages to rollbar period (default 30 seconds)
- ``bulk_report`` -- wether to send messages in a single http request or several (default false)

Contributing
------------

Contributions are welcome. The project is hosted on github at http://github.com/lrascao/rollbar-udp-agent

