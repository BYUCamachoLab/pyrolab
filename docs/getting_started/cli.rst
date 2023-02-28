.. _getting_started_cli:


Command Line Interface
======================

PyroLab infrastructure is managed through a command line interface (CLI) that
is inspired by Docker. If you are familiar, PyroLab's CLI may feel quite 
familiar. Knowledge of Docker's CLI is definitely not a requirement, though.

You can view all options in the PyroLab CLI by running ``pyrolab --help``:

.. code-block:: bash

    Usage: pyrolab [OPTIONS] COMMAND [ARGS]...

    Options:
    -v, --version                   Show the version and exit.
    --data-dir                      Show the data directories and exit.
    --install-completion [bash|zsh|fish|powershell|pwsh]
                                    Install completion for the specified shell.
    --show-completion [bash|zsh|fish|powershell|pwsh]
                                    Show completion for the specified shell, to
                                    copy it or customize the installation.
    --help                          Show this message and exit.

    Commands:
    config  Configure PyroLab nameservers, daemons, and services.
    down    Stop the background PyroLab daemon.
    info    Print details about a nameserver, daemon, or service.
    logs
    ps      Process status: list all running PyroLab nameservers, daemons,...
    reload  Reload the PyroLab daemon using the latest configuration file.
    rename  Rename a nameserver, daemon or service.
    start   Start a nameserver or daemon (and its services).
    stop    Stop a nameserver or daemon (and its services).
    up      Start the background PyroLab daemon.

PyroLab has an always-running daemon that manages services and other server
instances. The daemon can be started by running ``pyrolab up``. Any services
defined in the ``autolaunch`` section of the `YAML file
<getting_started_yaml>`_ will automatically be started at this time.

PyroLab also maintains an internal global configuration. It is in the same
format as the configuration file we wrote in the last section. You have to
explicitly load this configuration file into PyroLab before launching the
main daemon. You can do this with the ``pyrolab config`` utility:

.. code-block:: bash

    Usage: pyrolab config [OPTIONS] COMMAND [ARGS]...

    Configure PyroLab nameservers, daemons, and services.

    Options:
    --help  Show this message and exit.

    Commands:
    export  Export the configuration file
    reset   Reset the configuration file
    update  Update the configuration file

In our ``library-catalog`` example, you could load the configuration file:

.. code-block:: bash

    pyrolab config update config.yaml

Then you could start the monitoring PyroLab daemon by running:

.. code-block:: bash

    pyrolab up

Assuming you don't get any errors in the terminal, you can then run the process
status command:

.. code-block:: bash

    pyrolab ps

It will print to the terminal a nicely formatted table detailing all the 
running processes daemons and nameservers:

.. code-block:: text

    NAMESERVER    CREATED              STATUS        URI
    ------------  -------------------  ------------  -----
    production    2023-02-27 15:58:36  Up 7 seconds

    DAEMON    CREATED              STATUS        URI
    --------  -------------------  ------------  -----
    lockable  2023-02-27 15:58:36  Up 7 seconds

The PyroLab daemon monitors the server processes it starts up, automatically 
relaunching them if they fail or encounter an error at some point. 

Although PyroLab will just happily keep humming along in the background, if you
want to shutdown the server daemons and main PyroLab daemon, you can by running
``pyrolab down``. Don't do that yet, though--in the next section, we'll look at 
how to connect to your custom services from a remote client.
