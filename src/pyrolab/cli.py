# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Command Line Interface
======================

Usage: pyrolab [OPTIONS] COMMAND [ARGS]...

Try ``pyrolab --help`` for help.
"""
import platform
import shutil
import subprocess
import sys
import textwrap
import fileinput
import re
from pathlib import Path
from typing import Callable, Iterable, Optional
from time import sleep, strptime

import pkg_resources
import typer

from pyrolab import LOCKFILE, PYROLAB_LOGDIR, RUNTIME_CONFIG, USER_CONFIG_FILE
from pyrolab.api import Proxy
from pyrolab.configure import (
    PyroLabConfiguration,
    export_config,
    reset_config,
    update_config,
)
from pyrolab.pyrolabd import InstanceInfo, PyroLabDaemon


def get_daemon(abort=True, suppress_reload_message=False) -> PyroLabDaemon:
    if LOCKFILE.exists():
        ii = InstanceInfo.parse_file(LOCKFILE)
        DAEMON = Proxy(ii.uri)
        if not suppress_reload_message and RUNTIME_CONFIG.exists():
            if RUNTIME_CONFIG.stat().st_mtime < USER_CONFIG_FILE.stat().st_mtime:
                typer.secho(
                    "The configuration file has been updated. Run 'pyrolab reload' for changes to take effect.",
                    fg=typer.colors.RED
                )
        return DAEMON
    elif abort:
        typer.secho("PyroLab daemon is not running! Try 'pyrolab up' first.", fg=typer.colors.RED)
        raise typer.Abort()
    else:
        return None


###############################################################################
# pyrolab Main App
# 
# COMMANDS
# --------
# pyrolab up
# pyrolab down
# pyrolab reload
# pyrolab ps
# pyrolab --version
###############################################################################

app = typer.Typer(no_args_is_help=True)


def _version_callback(value: bool=True) -> None:
    if value:
        from pyrolab import __version__
        typer.echo(f"PyroLab {__version__}")
        raise typer.Exit()

def _show_data_dir(value: bool=True) -> None:
    if value:
        from pyrolab import PYROLAB_DATA_DIR
        typer.echo(f"{PYROLAB_DATA_DIR}")
        raise typer.Exit()

@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-v", help="Show the version and exit.", callback=_version_callback, is_eager=True),
    show_data_dir: bool = typer.Option(False, "--data-dir", help="Show the data directories and exit.", callback=_show_data_dir, is_eager=True),
):
    return

@app.command()
def up(
    port: int = typer.Option(None, "--port", "-p", help="Port to use for the PyroLab daemon."),
    force: bool = typer.Option(False, "--force", "-f", help="Force launch of the daemon (only if you're positive it has died!)."),
):
    """
    Start the background PyroLab daemon.

    Only use the `--force` flag if you're sure the daemon is dead, or you may
    orphan the process.
    """
    daemon = get_daemon(abort=False, suppress_reload_message=True)
    if daemon is None or force:
        if force and LOCKFILE.exists():
            LOCKFILE.unlink()
        
        rsrc = Path(pkg_resources.resource_filename('pyrolab', "pyrolabd.py"))
        
        if port:
            args = [sys.executable, str(rsrc), str(port)]
        else:
            args = [sys.executable, str(rsrc)]

        if platform.system() == "Windows":
            DETACHED_PROCESS = 0x00000008
            # Replace python.exe with pythonw.exe on Windows, usually in the
            # same directory (certainly true for conda installations).
            executable = Path(sys.exec_prefix) / "pythonw.exe"
            args[0] = str(executable)
            subprocess.Popen(args, close_fds=True, start_new_session=True, creationflags=DETACHED_PROCESS)
        else:
            subprocess.Popen(args, close_fds=True, start_new_session=True) # stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
        
        typer.secho("PyroLab daemon launched.", fg=typer.colors.GREEN)
    else:
        typer.secho("PyroLab daemon is already running!", fg=typer.colors.RED)
        raise typer.Abort()

@app.command()
def down():
    """
    Stop the background PyroLab daemon.
    """
    daemon = get_daemon(suppress_reload_message=True)
    daemon.shutdown()
    while LOCKFILE.exists():
        sleep(0.1)
    typer.secho("PyroLab daemon shutdown.", fg=typer.colors.GREEN)

@app.command()
def reload():
    """
    Reload the PyroLab daemon using the latest configuration file.

    Useful if the configuration file has been updated.
    """
    daemon = get_daemon(suppress_reload_message=True)
    result = daemon.reload()
    if result:
        typer.secho("PyroLab daemon reloaded.", fg=typer.colors.GREEN)
    else:
        typer.secho("PyroLab daemon reload failed.", fg=typer.colors.RED)

@app.command()
def ps():
    """
    Process status: list all running PyroLab nameservers, daemons, and services.
    """
    daemon = get_daemon()
    typer.echo(daemon.ps())

###############################################################################
# pyrolab config
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
    if USER_CONFIG_FILE.exists():
        shutil.copy(USER_CONFIG_FILE, filename)
    else:
        typer.secho("No configuration file found.", fg=typer.colors.RED)
        raise typer.Abort()

###############################################################################
# pyrolab start
###############################################################################

start_app = typer.Typer()
app.add_typer(start_app, name="start", help="Start a nameserver or daemon (and its services).")

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
# pyrolab stop
###############################################################################

stop_app = typer.Typer()
app.add_typer(stop_app, name="stop", help="Stop a nameserver or daemon (and its services).")

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
# pyrolab info
###############################################################################

info_app = typer.Typer()
app.add_typer(info_app, name="info", help="Print details about a nameserver, daemon, or service.")

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
# pyrolab logs
###############################################################################

logs_app = typer.Typer()
app.add_typer(logs_app, name="logs")

@logs_app.command("clean")
def logs_clean():
    """
    Deletes all log files.
    """
    [f.unlink() for f in PYROLAB_LOGDIR.glob("*.*")]

def try_itr(func: Callable, itr: Iterable, *exceptions, **kwargs):
    """
    Tests a function on an iterable, yields iterable if no exception is raised.
    """
    for elem in itr:
        try:
            func(elem, **kwargs)
            yield elem
        except exceptions:
            pass

@logs_app.command("export")
def logs_export(filename: str):
    """
    Exports the log file to a file.
    """
    f_names = PYROLAB_LOGDIR.glob('*.*')
    lines = list(fileinput.input(f_names))
    t_fmt = "%Y-%m-%d %H:%M:%S.%f" # format of time stamps
    t_pat = re.compile(r'\[(.+?)\]') # pattern to extract timestamp
    lines = list(try_itr(lambda l: strptime(t_pat.search(l).group(1), t_fmt), lines, AttributeError))
    with Path(filename).open(mode='w') as f:
        for l in sorted(lines, key=lambda l: strptime(t_pat.search(l).group(1), t_fmt)):
            f.write(l)
    typer.secho(f"Exported logs to {filename}", fg=typer.colors.GREEN)

###############################################################################
# pyrolab rename
###############################################################################

rename_app = typer.Typer()
app.add_typer(rename_app, name="rename", help="Rename a nameserver, daemon or service.")

@rename_app.command("nameserver")
def rename_nameserver(
    old_name: str, 
    new_name: str, 
):
    """
    Rename a nameserver.
    """
    if USER_CONFIG_FILE.exists():
        config = PyroLabConfiguration.from_file(USER_CONFIG_FILE)
        if old_name in config.nameservers:
            config.nameservers[new_name] = config.nameservers.pop(old_name)
            export_config(config, USER_CONFIG_FILE)
        else:
            typer.secho("Nameserver not found.", fg=typer.colors.RED)
            raise typer.Exit()
    else:
        typer.secho("No user configuration file found.", fg=typer.colors.RED)
        raise typer.Exit()

@rename_app.command("daemon")
def rename_daemon(
    old_name: str, 
    new_name: str, 
):
    """
    Rename a daemon.
    """
    if USER_CONFIG_FILE.exists():
        config = PyroLabConfiguration.from_file(USER_CONFIG_FILE)
        if old_name in config.daemons:
            config.daemons[new_name] = config.daemons.pop(old_name)
            export_config(config, USER_CONFIG_FILE)
        else:
            typer.secho("Nameserver not found.", fg=typer.colors.RED)
            raise typer.Exit()
    else:
        typer.secho("No user configuration file found.", fg=typer.colors.RED)
        raise typer.Exit()

@rename_app.command("service")
def rename_service(
    old_name: str, 
    new_name: str, 
):
    """
    Rename a service.
    """
    if USER_CONFIG_FILE.exists():
        config = PyroLabConfiguration.from_file(USER_CONFIG_FILE)
        if old_name in config.services:
            config.services[new_name] = config.services.pop(old_name)
            export_config(config, USER_CONFIG_FILE)
        else:
            typer.secho("Nameserver not found.", fg=typer.colors.RED)
            raise typer.Exit()
    else:
        typer.secho("No user configuration file found.", fg=typer.colors.RED)
        raise typer.Exit()

###############################################################################
# pyrolab restart
###############################################################################

restart_app = typer.Typer()
# app.add_typer(restart_app, name="restart")

###############################################################################
# pyrolab rm
###############################################################################

rm_app = typer.Typer()
# app.add_typer(rm_app, name="rm")

###############################################################################
# pyrolab add
###############################################################################

add_app = typer.Typer()
# app.add_typer(add_app, name="add")


if __name__ == "__main__":
    app()
