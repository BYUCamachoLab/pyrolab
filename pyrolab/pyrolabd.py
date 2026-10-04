# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
PyroLab Daemon
===============

Submodule defining the background PyroLab daemon.
"""

import logging
import os
import shutil
import sys
import threading
from typing import NamedTuple, Optional

import Pyro5.api as api
from pydantic import BaseModel
from tabulate import tabulate

from pyrolab import LOCKFILE, RUNTIME_CONFIG, STARTUP_ERROR_FILE, USER_CONFIG_FILE
from pyrolab.configure import GlobalConfiguration, describe_config_error
from pyrolab.manager import ProcessManager
from pyrolab.utils import pid_is_running

log = logging.getLogger("pyrolab.pyrolabd")


class InstanceInfo(BaseModel):
    """
    Model for storing information about a running instance.
    """

    pid: int
    uri: str


def write_lockfile(info: InstanceInfo) -> None:
    """
    Atomically write the lockfile.

    The contents go to a temporary file in the same directory, which then
    replaces the lockfile in one step, so readers see either no lockfile or a
    complete one, never a partial write.
    """
    tmp = LOCKFILE.with_name(f"{LOCKFILE.name}.{os.getpid()}.tmp")
    tmp.write_text(info.json())
    os.replace(tmp, LOCKFILE)


def read_lockfile() -> Optional[InstanceInfo]:
    """
    Return the running daemon's details from the lockfile.

    Returns None if there is no lockfile or it cannot be parsed. The PID may
    belong to a process that has since exited; check with
    :py:func:`pyrolab.utils.pid_is_running`.
    """
    try:
        return InstanceInfo.parse_file(LOCKFILE)
    except (OSError, ValueError):  # missing, unreadable, or not valid JSON
        return None


class NameServerInfo(NamedTuple):
    """
    Named tuple for storing information about a running nameserver.
    """

    name: str
    created: str
    status: str
    uri: str


class DaemonInfo(NamedTuple):
    """
    Named tuple for storing information about a running daemon.
    """

    name: str
    created: str
    status: str
    uri: str


class PSInfo(NamedTuple):
    """
    Named tuple for storing information about a running service.
    """

    name: str
    daemon: str
    uri: str


@api.expose
@api.behavior(instance_mode="single")
class PyroLabDaemon:
    """
    The PyroLab daemon runs continuously in the background.

    The daemon and controls all PyroLab entities through the PyroLabManager
    singleton. The main purpose of the daemon is to listen for requests and
    commands, usually sent through the command line interface (CLI).

    No script should ever need to import or instantiate the PyroLabDaemon.
    To preserve its "single instance" nature, the daemon should only be created
    and run through the CLI (which in turn, runs this module as a script).
    Limiting daemon manipulation to the CLI guarantees that only one daemon
    will be running at any given time (courtesy of the Lockfile this script
    creates and checks).

    By default, the daemon will load the user configuration file (manipulatable
    via the CLI) and write a runtime configuration file (not manipulatable via
    the CLI). The daemon will not change its configuration unless a call to the
    :py:func:`reload` method is made, usually by the CLI. Even if the user
    configuration file is changed, the daemon will not reload unless explictly
    instructed to do so. It is therefore of the utmost importance that the
    runtime configuration file be managed solely by the daemon! No touchy!

    .. note::
       As a Pyro5 object, no method of the daemon should return any types other
       than Python builtins, due to serialization issues.
    """

    def __init__(self):
        log.info("Starting PyroLab daemon.")
        # Load (and validate) the configuration before starting the process
        # manager, so an invalid configuration fails fast and leaves nothing
        # running.
        self.gconfig = GlobalConfiguration.instance()
        if USER_CONFIG_FILE.exists():
            self.gconfig.load_config(USER_CONFIG_FILE)
            self.gconfig.save_config(RUNTIME_CONFIG)
        self.manager = ProcessManager.instance()

    def autolaunch(self) -> None:
        """
        Starts every nameserver and daemon listed under ``autolaunch``.

        Each entry is started independently: one that fails is logged and the
        rest still start. Run in a background thread at startup, so the daemon
        answers requests while the entities come up.
        """
        log.info("Autolaunching PyroLab entities.")
        autodetails = self.gconfig.config.autolaunch
        for ns in autodetails.nameservers:
            try:
                self.start_nameserver(ns)
            except Exception:
                log.exception("Autolaunch of nameserver '%s' failed", ns)
        for daemon in autodetails.daemons:
            try:
                self.start_daemon(daemon)
            except Exception:
                log.exception("Autolaunch of daemon '%s' failed", daemon)
        log.info("Autolaunch complete.")

    def reload(self) -> bool:
        """
        Reloads the latest configuration file and restarts services that were
        running.

        Returns
        -------
        bool
            True if the reload was successful, False otherwise (including when
            there is no user configuration file to reload from, in which case
            nothing is changed).
        """
        log.debug("Daemon reload requested.")
        if not USER_CONFIG_FILE.exists():
            log.warning(
                "Reload skipped: no user configuration file at %s; running "
                "entities are left as they are.",
                USER_CONFIG_FILE,
            )
            return False
        shutil.copy(USER_CONFIG_FILE, RUNTIME_CONFIG)
        self.gconfig.load_config(RUNTIME_CONFIG)
        return self.manager.reload()

    def whoami(self) -> str:
        """
        Returns the object ID of the daemon, and it's PID number.
        """
        return f"{id(self)} at {os.getpid()}"

    def ps(self) -> str:
        """
        List all known processes grouped as nameservers, daemons, and services.

        Lists process names, status (i.e. running, stopped, etc.), start time,
        URI/ports, etc.
        """
        log.debug("Daemon process listing requested.")

        listing = []
        for ns in self.gconfig.get_config().nameservers.keys():
            info = self.manager.get_nameserver_process_info(ns)
            listing.append(NameServerInfo(name=ns, **info))
        nsstring = tabulate(listing, headers=["NAMESERVER", "CREATED", "STATUS", "URI"])

        listing = []
        for daemon in self.gconfig.get_config().daemons.keys():
            info = self.manager.get_daemon_process_info(daemon)
            listing.append(DaemonInfo(name=daemon, **info))
        daemonstring = tabulate(listing, headers=["DAEMON", "CREATED", "STATUS", "URI"])

        listing = []
        for service in self.gconfig.get_config().services.keys():
            info = self.manager.get_service_process_info(service)
            listing.append(PSInfo(service, **info))
        servicestring = tabulate(listing, headers=["SERVICE", "DAEMON", "URI"])

        return f"\n{nsstring}\n\n{daemonstring}\n\n{servicestring}\n"

    def start_nameserver(self, nameserver: str) -> None:
        """
        Starts a nameserver.

        Parameters
        ----------
        nameserver : str
            The name of the nameserver to start.
        """
        log.debug(f"Starting nameserver '{nameserver}'.")
        self.manager.launch_nameserver(nameserver)

    def start_daemon(self, daemon: str) -> None:
        """
        Starts a daemon.

        Parameters
        ----------
        daemon : str
            The name of the daemon to start.
        """
        log.debug(f"Starting daemon '{daemon}'.")
        self.manager.launch_daemon(daemon)

    def stop_nameserver(self, nameserver: str) -> bool:
        """
        Stops a nameserver.

        Parameters
        ----------
        nameserver : str
            The name of the nameserver to stop.

        Returns
        -------
        bool
            False if no nameserver by that name was running.
        """
        log.debug(f"Stopping nameserver '{nameserver}'.")
        return self.manager.shutdown_nameserver(nameserver)

    def stop_daemon(self, daemon: str) -> bool:
        """
        Stops a daemon.

        Parameters
        ----------
        daemon : str
            The name of the daemon to stop.

        Returns
        -------
        bool
            False if no daemon by that name was running.
        """
        log.debug(f"Stopping daemon '{daemon}'.")
        return self.manager.shutdown_daemon(daemon)

    def restart_nameserver(self, name: str) -> None:
        """
        Restarts a nameserver.

        Parameters
        ----------
        name : str
            The name of the nameserver to restart.
        """
        log.debug(f"Restarting nameserver '{name}'.")
        self.manager.shutdown_nameserver(name)
        self.manager.launch_nameserver(name)

    def restart_daemon(self, name: str) -> None:
        """
        Restarts a daemon.

        Parameters
        ----------
        name : str
            The name of the daemon to restart.
        """
        log.debug(f"Restarting daemon '{name}'.")
        self.manager.shutdown_daemon(name)
        self.manager.launch_daemon(name)

    @api.oneway
    def shutdown(self) -> None:
        """
        Shuts down the daemon.

        This method does not return a confirmation since, by nature of the
        shutdown request, the daemon will not be able to respond.
        """
        log.info("Daemon shutdown requested.")
        self.manager.shutdown_all()
        self._pyroDaemon.shutdown()
        log.info("Daemon shutdown complete.")


def _report_startup_error(message: str) -> None:
    """Log why the daemon could not start, and leave the reason for `up`."""
    log.error("PyroLab daemon failed to start: %s", message)
    try:
        STARTUP_ERROR_FILE.write_text(message)
    except OSError:
        log.exception("Could not write %s", STARTUP_ERROR_FILE)


def main(port: int = 0) -> int:
    """
    Runs the background daemon until it is shut down.

    The lockfile is published as soon as the daemon can answer requests;
    autolaunched entities start afterwards, in the background.

    Parameters
    ----------
    port : int, optional
        The port to serve on (default 0: any free port).

    Returns
    -------
    int
        The process exit code.
    """
    existing = read_lockfile()
    if existing is not None and pid_is_running(existing.pid):
        _report_startup_error(
            f"another PyroLab daemon is already running (pid {existing.pid})"
        )
        return 1

    daemon = None
    published = False
    try:
        daemon = api.Daemon(port=port)
        try:
            pyrolabd = PyroLabDaemon()
        except ValueError as e:  # includes pydantic's ValidationError
            problems = "\n".join(f"  - {line}" for line in describe_config_error(e))
            _report_startup_error(
                f"invalid configuration in {USER_CONFIG_FILE}:\n{problems}"
            )
            return 1
        uri = daemon.register(pyrolabd, "pyrolabd")
        write_lockfile(InstanceInfo(pid=os.getpid(), uri=str(uri)))
        published = True
        log.info("PyroLab daemon listening at %s", uri)

        threading.Thread(
            target=pyrolabd.autolaunch, name="autolaunch", daemon=True
        ).start()
        daemon.requestLoop()
        return 0
    except Exception as e:
        log.exception("PyroLab daemon stopped unexpectedly")
        if not published:
            _report_startup_error(f"{type(e).__name__}: {e}")
        return 1
    finally:
        # A normal shutdown already stopped everything; this covers failures.
        manager = ProcessManager._instance
        if manager is not None:
            manager.shutdown_all()
        if daemon is not None:
            daemon.close()
        current = read_lockfile()
        if current is not None and current.pid == os.getpid():
            LOCKFILE.unlink(missing_ok=True)
        RUNTIME_CONFIG.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 0))
