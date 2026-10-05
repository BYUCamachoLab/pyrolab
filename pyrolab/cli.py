# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Command Line Interface
======================

Usage: pyrolab [OPTIONS] COMMAND [ARGS]...

Try ``pyrolab --help`` for help.
"""

import json
import logging
import platform
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from time import sleep
from typing import Optional

from tabulate import tabulate

try:
    import importlib.resources as pkg_resources
except ImportError:
    import pkg_resources
import typer
import yaml
from Pyro5.errors import CommunicationError

import pyrolab
from pyrolab import (
    LEGACY_DATA_DIR,
    LEGACY_MIGRATION_MARKER,
    LOCKFILE,
    NAMESERVER_STORAGE,
    PYROLAB_LOGDIR,
    PYROLAB_LOGFILE,
    RUNTIME_CONFIG,
    STARTUP_ERROR_FILE,
    UPDATE_CHECK_FILE,
    USER_CONFIG_FILE,
    logs,
    updates,
)
from pyrolab.api import Proxy
from pyrolab.configure import (
    SECTIONS,
    PyroLabConfiguration,
    describe_config_error,
    export_config,
    rename_entity,
    reset_config,
    update_config,
)
from pyrolab.locations import DATA_DIR_ENV_VAR, migrate_legacy_files
from pyrolab.pyrolabd import PyroLabDaemon, read_lockfile
from pyrolab.utils import atomic_write_text, pid_is_running


def _print_config_problems(source, exc: Exception) -> None:
    typer.secho(f"Invalid configuration in {source}:", fg=typer.colors.RED)
    for line in describe_config_error(exc):
        typer.secho(f"  - {line}", fg=typer.colors.RED)


def _load_config_or_exit(path: Path) -> PyroLabConfiguration:
    try:
        return PyroLabConfiguration.from_file(path)
    except (ValueError, yaml.YAMLError) as e:
        _print_config_problems(path, e)
        raise typer.Exit(1)


def get_daemon(abort=True, suppress_reload_message=False) -> PyroLabDaemon:
    info = read_lockfile()
    if info is not None and pid_is_running(info.pid):
        try:
            DAEMON = Proxy(info.uri)
            DAEMON._pyroBind()
        except CommunicationError:
            raise ConnectionRefusedError(
                f"PyroLab daemon (pid {info.pid}) is running but not responding."
            )
        if (
            not suppress_reload_message
            and RUNTIME_CONFIG.exists()
            and USER_CONFIG_FILE.exists()
        ):
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
        rows = [
            ("Configuration", USER_CONFIG_FILE),
            ("Log file", PYROLAB_LOGFILE),
            ("Runtime state", LOCKFILE.parent),
            ("Nameserver data", NAMESERVER_STORAGE),
            ("Cache", UPDATE_CHECK_FILE.parent),
        ]
        for label, path in rows:
            typer.echo(f"{label + ':':17s}{path}")
        typer.echo(f"(Set {DATA_DIR_ENV_VAR} to keep everything in one directory.)")
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
        help="Show where PyroLab keeps its files and exit.",
        callback=_show_data_dir,
        is_eager=True,
    ),
):
    # Runs before every subcommand (but not --version or --data, which exit
    # first).
    copied = migrate_legacy_files(
        LEGACY_DATA_DIR, USER_CONFIG_FILE, NAMESERVER_STORAGE, LEGACY_MIGRATION_MARKER
    )
    if copied:
        typer.secho(
            "PyroLab now keeps its files outside the installed package. Copied "
            "from the old location (the originals are untouched):\n"
            + "".join(f"  {line}\n" for line in copied),
            fg=typer.colors.YELLOW,
            err=True,
        )
    # Checks PyPI at most once a day; see pyrolab.updates.
    latest = updates.check_for_update(pyrolab.__version__, UPDATE_CHECK_FILE)
    if latest:
        typer.secho(
            f"A new version of PyroLab is available ({latest}; you have "
            f"{pyrolab.__version__}). Set {updates.DISABLE_ENV_VAR} to turn "
            "off this check.",
            fg=typer.colors.YELLOW,
            err=True,
        )


def _spawn_daemon(port: Optional[int]) -> subprocess.Popen:
    """
    Launch pyrolabd.py as a detached background process.

    Its stdout and stderr (including tracebacks from crashing child
    processes) go to a file in the log directory, not the terminal that ran
    `pyrolab up`.
    """
    try:
        rsrc = pkg_resources.files(pyrolab) / "pyrolabd.py"
    except AttributeError:
        rsrc = Path(pkg_resources.resource_filename("pyrolab", "pyrolabd.py"))

    args = [sys.executable, str(rsrc)]
    if port:
        args.append(str(port))

    PYROLAB_LOGDIR.mkdir(parents=True, exist_ok=True)
    with open(PYROLAB_LOGDIR / DAEMON_OUTPUT_LOG, "ab") as output:
        options = dict(
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            close_fds=True,
            start_new_session=True,
        )
        if platform.system() == "Windows":
            DETACHED_PROCESS = 0x00000008
            # Replace python.exe with pythonw.exe on Windows, usually in the
            # same directory (certainly true for conda installations).
            args[0] = str(Path(sys.exec_prefix) / "pythonw.exe")
            options["creationflags"] = DETACHED_PROCESS
        return subprocess.Popen(args, **options)


DAEMON_OUTPUT_LOG = "pyrolabd_output.log"


def _daemon_responds(uri: str) -> bool:
    try:
        with Proxy(uri) as proxy:
            proxy._pyroTimeout = 2
            proxy._pyroBind()
        return True
    except CommunicationError:
        return False


@app.command()
def up(
    port: int = typer.Option(
        None, "--port", "-p", help="Port to use for the PyroLab daemon."
    ),
    timeout: float = typer.Option(
        30.0, "--timeout", help="Seconds to wait for the daemon to respond."
    ),
):
    """
    Start the background PyroLab daemon and wait until it responds.

    Nameservers and daemons listed under autolaunch keep starting in the
    background after this returns; check on them with `pyrolab ps`.
    """
    existing = read_lockfile()
    if existing is not None and pid_is_running(existing.pid):
        if _daemon_responds(existing.uri):
            typer.secho("PyroLab daemon is already running!", fg=typer.colors.RED)
        else:
            typer.secho(
                f"A PyroLab daemon (pid {existing.pid}) is running but not "
                "responding. It may still be starting; otherwise stop that "
                "process before running 'pyrolab up' again.",
                fg=typer.colors.RED,
            )
        raise typer.Abort()

    # Any lockfile left now is stale: its process is gone.
    LOCKFILE.unlink(missing_ok=True)
    STARTUP_ERROR_FILE.unlink(missing_ok=True)
    process = _spawn_daemon(port)

    deadline = time.monotonic() + timeout
    while True:
        info = read_lockfile()
        if info is not None and _daemon_responds(info.uri):
            typer.secho("PyroLab daemon is running.", fg=typer.colors.GREEN)
            return
        if process.poll() is not None:
            reason = (
                STARTUP_ERROR_FILE.read_text().strip()
                if STARTUP_ERROR_FILE.exists()
                else f"it exited with code {process.returncode}; see 'pyrolab logs "
                f"show' and {PYROLAB_LOGDIR / DAEMON_OUTPUT_LOG}"
            )
            typer.secho(
                f"PyroLab daemon failed to start: {reason}", fg=typer.colors.RED
            )
            raise typer.Exit(1)
        if time.monotonic() > deadline:
            typer.secho(
                f"PyroLab daemon did not respond within {timeout:g} seconds. It may "
                "still be starting; check with 'pyrolab status'.",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)
        sleep(0.2)


@app.command()
def down(
    timeout: float = typer.Option(
        60.0, "--timeout", help="Seconds to wait for everything to stop."
    ),
):
    """
    Stop the background PyroLab daemon and everything it runs.
    """
    daemon = get_daemon(suppress_reload_message=True)
    daemon.shutdown()
    # Stopping escalates to terminate/kill for anything that hangs, so this
    # normally finishes well within the timeout.
    deadline = time.monotonic() + timeout
    while LOCKFILE.exists():
        if time.monotonic() > deadline:
            typer.secho(
                f"PyroLab daemon has not exited after {timeout:g} seconds; see "
                "'pyrolab logs show'.",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)
        sleep(0.1)
    typer.secho("PyroLab daemon shutdown.", fg=typer.colors.GREEN)


@app.command()
def reload():
    """
    Reload the PyroLab daemon using the latest configuration file.

    Restarts everything that was running (if still configured) and starts every
    autolaunch entry.
    """
    daemon = get_daemon(suppress_reload_message=True)
    if not USER_CONFIG_FILE.exists():
        typer.secho(
            "No user configuration is installed, so there is nothing to reload "
            "from. Install one with 'pyrolab config update <file>' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    if daemon.reload():
        typer.secho("PyroLab daemon reloaded.", fg=typer.colors.GREEN)
    else:
        typer.secho(
            "PyroLab daemon reload failed; see the logs for details.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)


@app.command()
def ps():
    """
    Process status: list all running PyroLab nameservers, daemons, and services.
    """
    daemon = get_daemon()
    typer.echo(daemon.ps())


@app.command()
def status(
    lines: int = typer.Option(
        20, "--lines", "-n", help="Show at most this many (the most recent)."
    ),
):
    """
    Is the daemon running, and what has gone wrong since it started?

    Shows the warnings and errors logged since the daemon last started (or
    during its last run, if it has stopped).
    """
    info = read_lockfile()
    running = info is not None and pid_is_running(info.pid)
    if not running:
        typer.echo("PyroLab daemon is not running.")
    elif _daemon_responds(info.uri):
        typer.secho(
            f"PyroLab daemon is running (pid {info.pid}, {info.uri}).",
            fg=typer.colors.GREEN,
        )
    else:
        typer.secho(
            f"PyroLab daemon (pid {info.pid}) is running but not responding.",
            fg=typer.colors.YELLOW,
        )

    entries, _ = logs.read_entries(logs.log_files(PYROLAB_LOGFILE))
    if not entries:
        typer.echo(f"Nothing has been logged yet ({PYROLAB_LOGFILE}).")
        return
    problems = list(logs.at_least(logs.since_last_start(entries), logging.WARNING))
    when = "since it started" if running else "during its last run"
    if not problems:
        typer.echo(f"No warnings or errors {when}.")
        return
    shown = problems[-lines:] if lines > 0 else problems
    typer.echo(
        f"{len(problems)} warnings and errors {when}"
        + (f" (the last {len(shown)}):" if len(shown) < len(problems) else ":")
    )
    for entry in shown:
        typer.echo(logs.format_entry(entry, details=False))
    if any(e.get("exception") or e.get("stack") for e in shown):
        typer.echo("For tracebacks: pyrolab logs show --level warning")


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
    try:
        update_config(filename)
    except FileNotFoundError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(1)
    except (ValueError, yaml.YAMLError) as e:
        _print_config_problems(filename, e)
        typer.secho("The installed configuration was not changed.")
        raise typer.Exit(1)
    typer.secho("Configuration updated.", fg=typer.colors.GREEN)


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
        atomic_write_text(filename, USER_CONFIG_FILE.read_text())
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
    Start a nameserver and wait until it is serving.
    """
    daemon = get_daemon()
    _report_start("Nameserver", "nameserver", name, daemon.start_nameserver(name))


@start_app.command("daemon")
def start_daemon(name: str):
    """
    Start a daemon (and its services) and wait until it is serving.
    """
    daemon = get_daemon()
    _report_start("Daemon", "daemon", name, daemon.start_daemon(name))


def _report_start(label: str, kind: str, name: str, result: dict) -> None:
    status, error = result.get("status"), result.get("error", "")
    if status == "running":
        typer.secho(f"{label} '{name}' is running.", fg=typer.colors.GREEN)
    elif status == "already running":
        typer.secho(f"{label} '{name}' is already running.")
    elif status == "unknown":
        typer.secho(
            f"There is no {kind} named '{name}' in the configuration.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    elif status == "failed":
        typer.secho(f"{label} '{name}' failed to start: {error}", fg=typer.colors.RED)
        raise typer.Exit(1)
    else:
        typer.secho(
            f"{label} '{name}' did not report ready in time; check 'pyrolab ps'.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)


###############################################################################
# pyrolab stop
###############################################################################

stop_app = typer.Typer()
app.add_typer(
    stop_app, name="stop", help="Stop a nameserver or daemon (and its services)."
)


@stop_app.command("nameserver")
def stop_nameserver(
    name: str = typer.Argument(..., help="Name of the nameserver to stop"),
):
    """
    Stop a nameserver.
    """
    daemon = get_daemon()
    if not daemon.stop_nameserver(name):
        typer.secho(f"Nameserver '{name}' is not running.", fg=typer.colors.RED)
        raise typer.Exit(1)


@stop_app.command("daemon")
def stop_daemon(
    name: str = typer.Argument(..., help="Name of the daemon to stop"),
):
    """
    Stop a daemon.
    """
    daemon = get_daemon()
    if not daemon.stop_daemon(name):
        typer.secho(f"Daemon '{name}' is not running.", fg=typer.colors.RED)
        raise typer.Exit(1)


###############################################################################
# pyrolab info
###############################################################################


@app.command()
def info():
    """
    Show details about the current PyroLab configuration.
    """
    if RUNTIME_CONFIG.exists():
        config = _load_config_or_exit(RUNTIME_CONFIG)
    elif USER_CONFIG_FILE.exists():
        config = _load_config_or_exit(USER_CONFIG_FILE)
    else:
        typer.secho("No configuration installed.", fg=typer.colors.RED)
        raise typer.Exit()

    ns_data = []
    for name in config.nameservers:
        ns_data.append({"name": name, **config.nameservers[name].model_dump()})
    for item in ns_data:
        item["ns_autoclean"] = (
            f"{item['ns_autoclean']} sec" if item["ns_autoclean"] else "Off"
        )
    if ns_data:
        typer.echo("\nNameservers")
        typer.echo(tabulate(ns_data, headers="keys", tablefmt="rounded_grid"))

    daemon_data = []
    for name in config.daemons:
        daemon_data.append({"name": name, **config.daemons[name].model_dump()})
    for item in daemon_data:
        item["nameservers"] = "".join([f"- {name}\n" for name in item["nameservers"]])
    if daemon_data:
        typer.echo("\nDaemons")
        typer.echo(tabulate(daemon_data, headers="keys", tablefmt="rounded_grid"))

    service_data = []
    for name in config.services:
        service_data.append({"name": name, **config.services[name].model_dump()})
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
app.add_typer(logs_app, name="logs", help="Read, export, and clean up the log.")


def _parse_level(level: str) -> int:
    number = logs.find_level(level)
    if number is None:
        raise typer.BadParameter(f"unknown level '{level}' (e.g. DEBUG, INFO, WARNING)")
    return number


@logs_app.command("show")
def logs_show(
    level: str = typer.Option(
        "INFO", "--level", "-l", help="Show entries at this level and above."
    ),
    all_runs: bool = typer.Option(
        False, "--all", help="Include earlier runs of the daemon, not just the latest."
    ),
    lines: int = typer.Option(
        50, "--lines", "-n", help="Show at most this many (the most recent); 0 for all."
    ),
):
    """
    Show the log, from the daemon's most recent start.
    """
    minimum = _parse_level(level)
    entries, skipped = logs.read_entries(logs.log_files(PYROLAB_LOGFILE))
    if not all_runs:
        entries = logs.since_last_start(entries)
    selected = list(logs.at_least(entries, minimum))
    for entry in selected[-lines:] if lines > 0 else selected:
        typer.echo(logs.format_entry(entry))
    if not selected:
        typer.echo("No matching log entries.")
    if skipped:
        typer.secho(f"({skipped} unreadable lines skipped)", err=True)


@logs_app.command("export")
def logs_export(
    filename: str,
    as_json: bool = typer.Option(
        False, "--json", help="Write JSON lines (one entry per line) instead of text."
    ),
):
    """
    Write the whole log, oldest first, to a file.
    """
    entries, skipped = logs.read_entries(logs.log_files(PYROLAB_LOGFILE))
    lines = [json.dumps(e) if as_json else logs.format_entry(e) for e in entries]
    atomic_write_text(filename, "".join(f"{line}\n" for line in lines))
    typer.secho(
        f"Exported {len(entries)} log entries to {filename}", fg=typer.colors.GREEN
    )
    if skipped:
        typer.echo(f"Skipped {skipped} unreadable lines.")


@logs_app.command("clean")
def logs_clean():
    """
    Delete the log files. The daemon must be stopped first.
    """
    info = read_lockfile()
    if info is not None and pid_is_running(info.pid):
        typer.secho(
            "The PyroLab daemon is running and writing the log; stop it first "
            "('pyrolab down').",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    removed = 0
    for path in logs.log_files(PYROLAB_LOGFILE) + [PYROLAB_LOGDIR / DAEMON_OUTPUT_LOG]:
        try:
            path.unlink()
            removed += 1
        except FileNotFoundError:
            pass
        except OSError as e:
            typer.secho(f"Could not remove {path}: {e}", fg=typer.colors.RED)
    typer.echo(f"Removed {removed} log files.")


###############################################################################
# pyrolab rename
###############################################################################


def _rename(kind: str, old_name: str, new_name: str, force: bool) -> None:
    """Rename an entity in the user configuration, with every reference."""
    if not USER_CONFIG_FILE.exists():
        typer.secho("No user configuration file found.", fg=typer.colors.RED)
        raise typer.Exit(1)
    config = _load_config_or_exit(USER_CONFIG_FILE)
    entities = getattr(config, SECTIONS[kind])
    if old_name not in entities:
        typer.secho(f"{kind.capitalize()} '{old_name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)
    if new_name == old_name:
        typer.secho(f"{kind.capitalize()} '{old_name}' already has that name.")
        return
    if new_name in entities and not force:
        typer.secho(
            f"A {kind} named '{new_name}' already exists. Use --force to replace "
            "it (and point its references at the renamed one).",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    renamed, changes = rename_entity(config, kind, old_name, new_name)
    export_config(renamed, USER_CONFIG_FILE)

    typer.secho(f"Renamed {kind} '{old_name}' to '{new_name}'.", fg=typer.colors.GREEN)
    if changes:
        typer.echo("Updated references in: " + ", ".join(changes) + ".")
    if kind == "nameserver":
        before = config.nameservers[old_name]
        if before.storage in ("sql", "dbm"):
            after = renamed.nameservers[new_name]
            typer.secho(
                f"Note: its registrations are stored in "
                f"{before.get_storage_location().split(':', 1)[1]}; under the new "
                f"name it will use {after.get_storage_location().split(':', 1)[1]}. "
                "Move the file before reloading to keep them.",
                fg=typer.colors.YELLOW,
            )
    if kind == "service" or new_name in getattr(renamed.autolaunch, SECTIONS[kind]):
        # reload restarts the service's daemon, and starts autolaunch entries.
        typer.echo("Run 'pyrolab reload' to apply the new name.")
    else:
        # reload restarts what was running under names still configured; it
        # can't tell the renamed entity is the same one.
        typer.echo(
            f"If '{old_name}' is running, 'pyrolab reload' will stop it; then "
            f"start it under its new name with 'pyrolab start {kind} {new_name}'."
        )


rename_app = typer.Typer()
app.add_typer(rename_app, name="rename", help="Rename a nameserver, daemon or service.")

_FORCE = typer.Option(
    False, "--force", help="Replace an existing entity that already has the new name."
)


@rename_app.command("nameserver")
def rename_nameserver(old_name: str, new_name: str, force: bool = _FORCE):
    """
    Rename a nameserver, updating every service, daemon, and autolaunch entry
    that refers to it.
    """
    _rename("nameserver", old_name, new_name, force)


@rename_app.command("daemon")
def rename_daemon(old_name: str, new_name: str, force: bool = _FORCE):
    """
    Rename a daemon, updating every service and autolaunch entry that refers
    to it.
    """
    _rename("daemon", old_name, new_name, force)


@rename_app.command("service")
def rename_service(old_name: str, new_name: str, force: bool = _FORCE):
    """
    Rename a service.
    """
    _rename("service", old_name, new_name, force)


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


def run() -> None:
    """
    The ``pyrolab`` command.

    Applies process-wide settings (remote tracebacks, warnings, logging to
    stderr if PYROLAB_LOGLEVEL is set) here rather than in ``app``, so that
    using the app in-process, as the tests do, changes nothing global.
    """
    logs.configure_process()
    logs.configure_cli_logging()
    app()


if __name__ == "__main__":
    run()
