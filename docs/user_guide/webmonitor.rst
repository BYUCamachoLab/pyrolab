.. _user_guide_webmonitor:


Web Monitor
===========

PyroLab includes a web monitoring app that can be configured to display 
devices registered with a nameserver, along with their status (such as 
availability or locked state). It installs with PyroLab as an extra if you use
the command:

.. code-block:: bash

    pip install pyrolab[monitor]

It comes with a web server that can be configured to host the webapp on 
localhost or any other interface. It's launched using the command line, and you
can see it's options by typing ``pyromonitor --help``:

.. code-block:: text

    Usage: pyromonitor [OPTIONS] COMMAND [ARGS]...

    Options:
    -v, --version                   Show the version and exit.
    --install-completion [bash|zsh|fish|powershell|pwsh]
                                    Install completion for the specified shell.
    --show-completion [bash|zsh|fish|powershell|pwsh]
                                    Show completion for the specified shell, to
                                    copy it or customize the installation.
    --help                          Show this message and exit.

    Commands:
    configure  Load a server configuration file.
    up         Launch the monitoring web app.

The server configuration file is a YAML file with the following keys and 
defaults:

.. code-block:: yaml

    host: localhost
    port: 8080
    nameserver: localhost
    ns_port: 9090
    polling: 300

* ``host`` is the location to serve the web app, either localhost or your own
  IP address.
* ``port`` is the port to serve the web app on.
* ``nameserver`` is the domain of the nameserver to monitor.
* ``ns_port`` is the port the nameserver is exposed on.
* ``polling`` is the period in seconds between refreshes. The web monitor works
  by attempting to ping every listed service at a set refresh rate.

You can write your own configuration file and persist it within pyromonitor.
Only non-default keys need to be specified in this file, although you may 
specify all keys and values if you wish. Load the config file in pyromonitor
using the ``pyromonitor configure`` command:

.. code-block:: text

    Usage: pyromonitor configure [OPTIONS] FILENAME

    Load a server configuration file.

    Arguments:
    FILENAME  [required]

    Options:
    --help  Show this message and exit.

You can launch the monitor on the host and port in the configuration by using
the ``pyromonitor up`` command:

.. code-block:: text

    Serving on http://localhost:8080
    (press CTRL+C to quit)
