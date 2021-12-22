# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Command Line Interface
=======================

You should be able to find all background pyrolab daemons by running (on Unix):

```
ps aux | grep pyrolabd
```


Autoreload when watching a directory? 
* watchdog
* watchgod
"""
import subprocess
from typing import Optional
import pkg_resources
from pathlib import Path

import typer

from pyrolab.api import Proxy
from pyrolab.configure import update_config, reset_config, export_config
from pyrolab.pyrolabd import PyroLabDaemon, InstanceInfo, LOCKFILE


def get_daemon(abort=True) -> PyroLabDaemon:
    if LOCKFILE.exists():
        ii = InstanceInfo.parse_file(LOCKFILE)
        DAEMON = Proxy(ii.uri)
        return DAEMON
    elif abort:
        typer.secho("PyroLab daemon is not running! Try 'pyrolab launch' first.", fg=typer.colors.RED)
        raise typer.Abort()
    else:
        return None


###############################################################################
# pyrolab Main App
# 
# COMMANDS
# --------
# pyrolab launch
# pyrolab shutdown
# pyrolab ps
# pyrolab --version
###############################################################################

app = typer.Typer()

def _version_callback(value: bool) -> None:
    if value:
        from pyrolab import __version__
        typer.echo(f"PyroLab {__version__}")
        raise typer.Exit()

@app.callback()
def main(version: bool = typer.Option(False, "--version", "-v", help="Show the version and exit.", callback=_version_callback, is_eager=True)):
    return

@app.command()
def launch():
    """
    Launch the PyroLab daemon.

    # TODO: Add options for port number
    """
    daemon = get_daemon(abort=False)
    if daemon is None:
        rsrc = Path(pkg_resources.resource_filename('pyrolab', "pyrolabd.py"))
        DETACHED_PROCESS = 0x00000008
        subprocess.Popen(["python", f"{str(rsrc)}"], close_fds=True, start_new_session=True, creationflags=DETACHED_PROCESS) # stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
        typer.secho("PyroLab daemon launched.", fg=typer.colors.GREEN)
    else:
        typer.secho("PyroLab daemon is already running!", fg=typer.colors.GREEN)

@app.command()
def shutdown():
    """
    Shutdown the PyroLab daemon.
    """
    daemon = get_daemon()
    daemon.shutdown()
    typer.secho("PyroLab daemon shutdown", fg=typer.colors.GREEN)

@app.command()
def reset():
    """
    Removes the lock file that tracks the PyroLab daemon's state.
    """
    typer.confirm("Only do this if you are sure the daemon is not running, or you may orphan the process. Continue?", abort=True)
    if LOCKFILE.exists():
        LOCKFILE.unlink()
        typer.secho("PyroLab daemon reset", fg=typer.colors.GREEN)
    else:
        typer.secho("PyroLab daemon is not running!", fg=typer.colors.GREEN)

@app.command()
def ps():
    """
    List all running PyroLab nameservers, daemons, and services.
    """
    daemon = get_daemon()
    typer.echo(daemon.ps())


###############################################################################
# pyrolab Config App
#
# COMMANDS
# --------
# pyrolab config update FILENAME
# pyrolab config reset
# pyrolab config export FILENAME
###############################################################################

config_app = typer.Typer()
app.add_typer(config_app, name="config", help="Configure PyroLab nameservers, daemons, and services.")

@config_app.command("update")
def config_update(filename: str):
    """Update the configuration file"""
    update_config(filename)
    
@config_app.command("reset")
def config_reset():
    """Reset the configuration file"""
    delete = typer.confirm("Are you sure you want to reset the configuration? This cannot be undone.")
    if not delete:
        typer.secho("No changes made.", fg=typer.colors.GREEN)
        raise typer.Exit()
    reset_config()
    typer.secho("Configuration reset.", fg=typer.colors.RED)

@config_app.command("export")
def config_export(filename: str):
    """Export the configuration file"""
    export_config(filename)


###############################################################################
# pyrolab Start App
#
# COMMANDS
# --------
# pyrolab start NAME
# pyrolab start -ns --nameserver NAME
# pyrolab start -d --daemon NAME
###############################################################################

start_app = typer.Typer()
app.add_typer(start_app, name="start")

@start_app.callback()
def start_something(name: Optional[str] = typer.Argument(None, help="Name of the service to start"),):
    """
    Start a nameserver, daemon, or service.
    """
    # TODO: If "all" requested, start all services
    print(name)
    raise typer.Exit()

# @start_app.command("nameserver")


###############################################################################
# pyrolab Stop App
#
# COMMANDS
# --------
# pyrolab stop NAME
# pyrolab stop nameserver NAME
# pyrolab stop daemon NAME
###############################################################################

stop_app = typer.Typer()
app.add_typer(stop_app, name="stop")

@stop_app.callback()
def stop_any(self, name: Optional[str] = typer.Argument(None, help="Name of the service to stop"),):
    """
    Stop a nameserver, daemon, or service.
    """
    pass

@stop_app.command("nameserver")
def stop_nameserver(name: Optional[str] = typer.Argument(None, help="Name of the service to stop"),):
    """
    Stop a nameserver.
    """
    pass

@stop_app.command("daemon")
def stop_daemon(name: Optional[str] = typer.Argument(None, help="Name of the service to stop"),):
    """
    Stop a daemon.
    """
    pass

###############################################################################
# pyrolab Info App
#
# COMMANDS
# --------
# pyrolab info NAME --verbose
###############################################################################

info_app = typer.Typer()
# app.add_typer(info_app, name="info")

# Accept --verbose as an argument, which gives nameserver details, too


###############################################################################
# pyrolab Logs App
#
# COMMANDS
# --------
# pyrolab logs NAME
###############################################################################

logs_app = typer.Typer()
# app.add_typer(logs_app, name="logs")


###############################################################################
# pyrolab Rename App
#
# COMMANDS
# --------
# pyrolab rename OLDNAME NEWNAME
###############################################################################

rename_app = typer.Typer()
# app.add_typer(rename_app, name="rename")


###############################################################################
# pyrolab Restart App
#
# COMMANDS
# --------
# pyrolab restart NAME
###############################################################################

restart_app = typer.Typer()
# app.add_typer(restart_app, name="restart")


###############################################################################
# pyrolab Remove App
#
# COMMANDS
# --------
# pyrolab rm NAME
###############################################################################

rm_app = typer.Typer()
# app.add_typer(rm_app, name="rm")


###############################################################################
# pyrolab Add App
#
# COMMANDS
# --------
# pyrolab add nameserver NAME
# pyrolab add daemon NAME
# pyrolab add service NAME
###############################################################################

add_app = typer.Typer()
# app.add_typer(add_app, name="add")


if __name__ == "__main__":
    app()
