pyrolab.cli
===========

.. automodule:: pyrolab.cli

.. code:: bash
   
   Usage: pyrolab [OPTIONS] COMMAND [ARGS]...
   
   Options:
     -v, --version                   Show the version and exit.
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


Where did my instances go?
--------------------------

You should be able to find all background pyrolab daemons by running (on Unix):

.. code-block:: bash

   ps aux | grep pyrolabd

Output of ``pyrolab --help``: