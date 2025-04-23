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
from tabulate import tabulate

try:
    import importlib.resources as pkg_resources
except ImportError:
    import pkg_resources
import typer
from Pyro5.errors import CommunicationError

import pyrolab
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
        try:
            DAEMON = Proxy(ii.uri)
            DAEMON._pyroBind()
        except CommunicationError:
            raise ConnectionRefusedError("Could not connect to daemon.")
        if not suppress_reload_message and RUNTIME_CONFIG.exists():
            if RUNTIME_CONFIG.stat().st_mtime < USER_CONFIG_FILE.stat().st_mtime:
                typer.secho(
                    "The configuration file has been updated. Run 'pyrolab reload' for changes to take effect.",
                    fg=typer.colors.RED,
                )
        return DAEMON
    elif abort:
        typer.secho(
            "PyroLab daemon is not running! Try 'pyrolab up' first.",
            fg=typer.colors.RED,
        )
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


def _version_callback(value: bool = True) -> None:
    if value:
        from pyrolab import __version__

        typer.echo(f"PyroLab {__version__}")
        raise typer.Exit()


def _show_data_dir(value: bool = True) -> None:
    if value:
        from pyrolab import PYROLAB_DATA_DIR

        typer.echo(f"{PYROLAB_DATA_DIR}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show the version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
    show_data_dir: bool = typer.Option(
        False,
        "--data",
        "-d",
        help="Show the data directories and exit.",
        callback=_show_data_dir,
        is_eager=True,
    ),
):
    return


@app.command()
def up(
    port: int = typer.Option(
        None, "--port", "-p", help="Port to use for the PyroLab daemon."
    ),
):
    """
    Start the background PyroLab daemon.

    Only use the `--force` flag if you're sure the daemon is dead, or you may
    orphan the process.
    """
    try:
        daemon = get_daemon(abort=False, suppress_reload_message=True)
        force = False
    except ConnectionRefusedError:
        daemon = None
        force = True
    if daemon is None or force:
        if force and LOCKFILE.exists():
            LOCKFILE.unlink()

        try:
            rsrc = pkg_resources.files(pyrolab) / "pyrolabd.py"
        except AttributeError:
            rsrc = Path(pkg_resources.resource_filename("pyrolab", "pyrolabd.py"))

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
            subprocess.Popen(
                args,
                close_fds=True,
                start_new_session=True,
                creationflags=DETACHED_PROCESS,
            )
        else:
            subprocess.Popen(
                args, close_fds=True, start_new_session=True
            )  # stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,

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
app.add_typer(
    config_app,
    name="config",
    help="Configure PyroLab nameservers, daemons, and services.",
)


@config_app.command("update")
def config_update(filename: str):
    """Update the configuration file"""
    update_config(filename)


@config_app.command("reset")
def config_reset():
    """Reset the configuration file"""
    delete = typer.confirm(
        "Are you sure you want to reset the configuration? This cannot be undone."
    )
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
app.add_typer(
    start_app, name="start", help="Start a nameserver or daemon (and its services)."
)


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
app.add_typer(
    stop_app, name="stop", help="Stop a nameserver or daemon (and its services)."
)


@stop_app.command("nameserver")
def stop_nameserver(
    name: Optional[str] = typer.Argument(None, help="Name of the service to stop"),
):
    """
    Stop a nameserver.
    """
    daemon = get_daemon()
    daemon.stop_nameserver(name)


@stop_app.command("daemon")
def stop_daemon(
    name: Optional[str] = typer.Argument(None, help="Name of the service to stop"),
):
    """
    Stop a daemon.
    """
    daemon = get_daemon()
    daemon.stop_daemon(name)


###############################################################################
# pyrolab info
###############################################################################


@app.command()
def info():
    """
    Show details about the current PyroLab configuration.
    """
    if RUNTIME_CONFIG.exists():
        config = PyroLabConfiguration.from_file(RUNTIME_CONFIG)
    elif USER_CONFIG_FILE.exists():
        config = PyroLabConfiguration.from_file(USER_CONFIG_FILE)
    else:
        typer.secho("No configuration installed.", fg=typer.colors.RED)
        raise typer.Exit()

    ns_data = []
    for name in config.nameservers:
        ns_data.append({"name": name, **config.nameservers[name].dict()})
    for item in ns_data:
        item["ns_autoclean"] = (
            f'{item["ns_autoclean"]} sec' if item["ns_autoclean"] else "Off"
        )
    if ns_data:
        typer.echo("\nNameservers")
        typer.echo(tabulate(ns_data, headers="keys", tablefmt="rounded_grid"))

    daemon_data = []
    for name in config.daemons:
        daemon_data.append({"name": name, **config.daemons[name].dict()})
    for item in daemon_data:
        item["nameservers"] = "".join([f"- {name}\n" for name in item["nameservers"]])
    if daemon_data:
        typer.echo("\nDaemons")
        typer.echo(tabulate(daemon_data, headers="keys", tablefmt="rounded_grid"))

    service_data = []
    for name in config.services:
        service_data.append({"name": name, **config.services[name].dict()})
    for item in service_data:
        item["parameters"] = "".join(
            [f"{k}: {v}\n" for k, v in item["parameters"].items()]
        )
        item["nameservers"] = "".join([f"- {name}\n" for name in item["nameservers"]])
    if service_data:
        typer.echo("\nServices")
        typer.echo(tabulate(service_data, headers="keys", tablefmt="rounded_grid"))


###############################################################################
# pyrolab logs
###############################################################################

logs_app = typer.Typer()
app.add_typer(logs_app, name="logs", help="Compile and export log files.")


@logs_app.command("clean")
def logs_clean():
    """
    Deletes all log files.
    """
    for f in PYROLAB_LOGDIR.glob("*.*"):
        # Try to delete file if not in use
        try:
            f.unlink()
        except PermissionError:
            pass


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
    f_names = PYROLAB_LOGDIR.glob("*.*")
    lines = list(fileinput.input(f_names))
    t_fmt = "%Y-%m-%d %H:%M:%S.%f"  # format of time stamps
    t_pat = re.compile(r"\[(.+?)\]")  # pattern to extract timestamp

    # Group lines into log entries
    log_entries = []
    current_entry = []
    for line in lines:
        # If we've found a new timestamp and we have a current entry, add it to
        # the list and start a new entry.
        if t_pat.match(line) and current_entry:
            log_entries.append("".join(current_entry))
            current_entry = [line]
        # Otherwise, keep extending the current entry.
        else:
            current_entry.append(line)
    # Add the last entry to the list
    if current_entry:
        log_entries.append("".join(current_entry))

    # Sort log entries by timestamp
    log_entries = sorted(
        log_entries, key=lambda entry: strptime(t_pat.search(entry).group(1), t_fmt)
    )

    # Write sorted log entries to the output file
    with Path(filename).open(mode="w") as f:
        for entry in log_entries:
            f.write(entry)
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
# pyrolab ns_list
###############################################################################


@app.command("nslist")
def ns_list(
    host: str = typer.Option(
        "localhost",
        "--host",
        "-h",
        help="Nameserver host to list all registered services for (default localhost).",
    ),
    port: int = typer.Option(
        9090, "--port", "-p", help="Port to use for the PyroLab daemon (default 9090)."
    ),
):
    """
    List all services registered with a nameserver.
    """
    from pyrolab.api import locate_ns

    ns = locate_ns(host=host, port=port)
    services = ns.list(return_metadata=True)

    listing = []
    for k, v in services.items():
        name = k
        uri, description = v
        listing.append([name, uri, ": ".join(description)])

    typer.echo(tabulate(listing, headers=["NAME", "URI", "DESCRIPTION"]))


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
