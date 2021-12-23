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
import shutil
import subprocess
import platform
import sys
import textwrap
from typing import Optional
import pkg_resources
from pathlib import Path
from tabulate import tabulate

import typer

from pyrolab import USER_CONFIG_FILE
from pyrolab.api import Proxy
from pyrolab.configure import PyroLabConfiguration, update_config, reset_config
from pyrolab.pyrolabd import PyroLabDaemon, InstanceInfo, LOCKFILE, RUNTIME_CONFIG


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
# pyrolab reload
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
def main(
    version: bool = typer.Option(False, "--version", "-v", help="Show the version and exit.", callback=_version_callback, is_eager=True)
):
    return

@app.command()
def launch(
    port: int = typer.Option(None, "--port", "-p", help="Port to use for the PyroLab daemon."),
    force: bool = typer.Option(False, "--force", "-f", help="Force launch of the daemon (only if you're positive it has died!)."),
):
    """
    Launch the PyroLab daemon.

    Only use the `--force` flag if you're sure the daemon is dead, or you may
    orphan the process.
    """
    daemon = get_daemon(abort=False)
    if daemon is None or force:
        if force:
            LOCKFILE.unlink()
        
        rsrc = Path(pkg_resources.resource_filename('pyrolab', "pyrolabd.py"))
        
        if port:
            args = [sys.executable, str(rsrc), str(port)]
        else:
            args = [sys.executable, str(rsrc)]
        
        if platform.system() == "Windows":
            DETACHED_PROCESS = 0x00000008
            subprocess.Popen(args, close_fds=True, start_new_session=True, creationflags=DETACHED_PROCESS)
        else:
            subprocess.Popen(args, close_fds=True, start_new_session=True) # stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
        
        typer.secho("PyroLab daemon launched.", fg=typer.colors.GREEN)
    else:
        typer.secho("PyroLab daemon is already running!", fg=typer.colors.RED)
        raise typer.Abort()

@app.command()
def shutdown():
    """
    Shutdown the PyroLab daemon.
    """
    daemon = get_daemon()
    daemon.shutdown()
    typer.secho("PyroLab daemon shutdown", fg=typer.colors.GREEN)

@app.command()
def reload():
    """
    Reload the PyroLab daemon using the latest configuration file.

    Useful if the configuration file has been updated.
    """
    daemon = get_daemon()
    result = daemon.reload()
    if result:
        typer.secho("PyroLab daemon reloaded.", fg=typer.colors.GREEN)
    else:
        typer.secho("PyroLab daemon reload failed.", fg=typer.colors.RED)

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
# pyrolab config save
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
    daemon = get_daemon(abort=False)
    if daemon:
        daemon.config_export(filename)
    elif USER_CONFIG_FILE.exists():
        shutil.copy(USER_CONFIG_FILE, filename)
    else:
        typer.secho("No configuration file found.", fg=typer.colors.RED)
        raise typer.Abort()

@config_app.command("save")
def config_save():
    """
    Save the current daemon configuration to the user configuration file.
    
    Requires that the background daemon be running.
    """
    daemon = get_daemon()
    if daemon:
        daemon.config_export(USER_CONFIG_FILE)
    else:
        typer.secho("Save only valid when daemon is running.", fg=typer.colors.RED)
        raise typer.Abort()

###############################################################################
# pyrolab Start App
#
# COMMANDS
# --------
# pyrolab start nameserver NAME
# pyrolab start daemon NAME
###############################################################################

start_app = typer.Typer()
app.add_typer(start_app, name="start", help="Start a nameserver, daemon, or service.")

@start_app.command("nameserver")
def start_nameserver(name: str):
    """
    Start a nameserver.
    """
    daemon = get_daemon()
    daemon.start_nameserver(name)

@start_app.command("daemon")
def start_daemon(name: str):
    """
    Start a daemon.
    """
    daemon = get_daemon()
    daemon.start_daemon(name)

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
    daemon = get_daemon()
    daemon.stop_nameserver(name)

@stop_app.command("daemon")
def stop_daemon(name: Optional[str] = typer.Argument(None, help="Name of the service to stop"),):
    """
    Stop a daemon.
    """
    daemon = get_daemon()
    daemon.stop_daemon(name)

###############################################################################
# pyrolab Info App
#
# COMMANDS
# --------
# pyrolab info nameserver NAME --verbose
# pyrolab info daemon NAME --verbose
# pyrolab info service NAME --verbose
###############################################################################

info_app = typer.Typer()
app.add_typer(info_app, name="info")

@info_app.command("nameserver")
def info_nameserver(
    name: str, 
):
    """
    Get information on a nameserver.
    """
    if RUNTIME_CONFIG.exists():
        config = PyroLabConfiguration.from_file(RUNTIME_CONFIG)
    elif USER_CONFIG_FILE.exists():
        config = PyroLabConfiguration.from_file(USER_CONFIG_FILE)
    else:
        typer.secho("No configuration file found.", fg=typer.colors.RED)
        raise typer.Exit()

    if name in config.nameservers:
        info = textwrap.indent(str(config.nameservers[name].yaml()), '  ')
        typer.echo(f"{name}\n{info}")
    else:
        typer.secho("Nameserver not found.", fg=typer.colors.RED)
        raise typer.Exit()

@info_app.command("daemon")
def info_daemon(
    name: str, 
):
    """
    Get information on a daemon.
    """
    if RUNTIME_CONFIG.exists():
        config = PyroLabConfiguration.from_file(RUNTIME_CONFIG)
    elif USER_CONFIG_FILE.exists():
        config = PyroLabConfiguration.from_file(USER_CONFIG_FILE)
    else:
        typer.secho("No configuration file found.", fg=typer.colors.RED)
        raise typer.Exit()

    if name in config.daemons:
        info = textwrap.indent(str(config.daemons[name].yaml()), '  ')
        typer.echo(f"{name}\n{info}")
    else:
        typer.secho("Daemon not found.", fg=typer.colors.RED)
        raise typer.Exit()

@info_app.command("service")
def info_service(
    name: str, 
):
    """
    Get information on a service.
    """
    if RUNTIME_CONFIG.exists():
        config = PyroLabConfiguration.from_file(RUNTIME_CONFIG)
    elif USER_CONFIG_FILE.exists():
        config = PyroLabConfiguration.from_file(USER_CONFIG_FILE)
    else:
        typer.secho("No configuration file found.", fg=typer.colors.RED)
        raise typer.Exit()

    if name in config.services:
        info = textwrap.indent(str(config.services[name].yaml()), '  ')
        typer.echo(f"{name}\n{info}")
    else:
        typer.secho("Service not found.", fg=typer.colors.RED)
        typer.echo(config.services.keys())
        raise typer.Exit()

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
app.add_typer(rename_app, name="rename")

@rename_app.command("nameserver")
def rename_nameserver(
    old_name: str, 
    new_name: str, 
):
    """
    Rename a nameserver.
    """
    daemon = get_daemon()
    daemon.rename_nameserver(old_name, new_name)

@rename_app.command("daemon")
def rename_daemon(
    old_name: str, 
    new_name: str, 
):
    """
    Rename a daemon.
    """
    daemon = get_daemon()
    daemon.rename_daemon(old_name, new_name)

@rename_app.command("service")
def rename_service(
    old_name: str, 
    new_name: str, 
):
    """
    Rename a service.
    """
    daemon = get_daemon()
    daemon.rename_service(old_name, new_name)

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
