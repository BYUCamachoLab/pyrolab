# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
PyroLab Daemon
--------------

Submodule defining the background PyroLab daemon.
"""

import logging
import os
import shutil
from typing import NamedTuple

import Pyro5.api as api
from pydantic import BaseModel
from tabulate import tabulate

from pyrolab import LOCKFILE, RUNTIME_CONFIG, USER_CONFIG_FILE
from pyrolab.configure import GlobalConfiguration
from pyrolab.manager import ProcessManager

log = logging.getLogger("pyrolab.pyrolabd")


class InstanceInfo(BaseModel):
    pid: int
    uri: str


class NameServerInfo(NamedTuple):
    name: str
    created: str
    status: str
    uri: str


class DaemonInfo(NamedTuple):
    name: str
    created: str
    status: str
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
    and run through the CLI (which in turn, runs this file as a script). 
    Limiting daemon manipulation to the CLI guarantees that only one daemon
    will be running at any given time (courtesy of the Lockfile this script
    creates and checks).

    By default, the daemon will load the user configuration file (manipulatable
    via the CLI) and write a runtime configuration file (not manipulatable via
    the CLI). The daemon will not change its configuration unless a call to the
    reload() method is made, usually by the CLI. Even if the user configuration
    file is changed, the daemon will not reload unless explictly instructed to
    do so. It is therefore of the utmost importance that the runtime 
    configuration file be managed solely by the daemon! No touchy!

    .. note::
       As a Pyro5 object, no method of the daemon should return any types other
       than Python builtins, due to serialization issues.
    """
    def __init__(self):
        log.info("Starting PyroLab daemon.")
        self.manager = ProcessManager.instance()

        if USER_CONFIG_FILE.exists():
            self.gconfig = GlobalConfiguration.instance()
            self.gconfig.load_config(USER_CONFIG_FILE)
            self.gconfig.save_config(RUNTIME_CONFIG)
        else:
            self.gconfig = GlobalConfiguration.instance()

        log.info("Autolaunching Pyrolab entities.")
        autodetails = self.gconfig.config.autolaunch
        for ns in autodetails.nameservers:
            self.start_nameserver(ns)
        for daemon in autodetails.daemons:
            self.start_daemon(daemon)
        log.info("PyroLab daemon started.")

    def reload(self) -> bool:
        """
        Reloads the latest configuration file and restarts services that were 
        running.

        Returns
        -------
        bool
            True if the reload was successful, False otherwise.
        """
        log.debug("Daemon reload requested.")
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
        nsstring = tabulate(listing, headers=['NAMESERVER', 'CREATED', 'STATUS', 'URI'])

        listing = []
        for daemon in self.gconfig.get_config().daemons.keys():
            info = self.manager.get_daemon_process_info(daemon)
            listing.append(DaemonInfo(name=daemon, **info))
        daemonstring = tabulate(listing, headers=['DAEMON', 'CREATED', 'STATUS', 'URI'])
        
        # for service in self.gconfig.get_config().services.keys():
        #     listing.append(PSInfo(service, "service", "", "", ""))
        
        return f"\n{nsstring}\n\n{daemonstring}\n"

    def start_nameserver(self, nameserver: str):
        log.debug(f"Starting nameserver '{nameserver}'.")
        self.manager.launch_nameserver(nameserver)

    def start_daemon(self, daemon: str):
        log.debug(f"Starting daemon '{daemon}'.")
        self.manager.launch_daemon(daemon)

    def stop_nameserver(self, nameserver: str):
        log.debug(f"Stopping nameserver '{nameserver}'.")
        self.manager.shutdown_nameserver(nameserver)

    def stop_daemon(self, daemon: str):
        log.debug(f"Stopping daemon '{daemon}'.")
        self.manager.shutdown_daemon(daemon)

    def restart_nameserver(self, name: str):
        log.debug(f"Restarting nameserver '{name}'.")
        self.manager.shutdown_nameserver(name)
        self.manager.launch_nameserver(name)

    def restart_daemon(self, name: str):
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


if __name__ == "__main__":
    if LOCKFILE.exists():
        raise RuntimeError(f"Lockfile already exists. Is another instance running?")
    else:
        try:
            LOCKFILE.touch(exist_ok=False)

            import sys
            if len(sys.argv) > 1:
                port = int(sys.argv[1])
            else:
                port = 0

            daemon = api.Daemon(port=port)
            pyrolabd = PyroLabDaemon()
            uri = daemon.register(pyrolabd, "pyrolabd")
            ii = InstanceInfo(pid=os.getpid(), uri=str(uri))
            with LOCKFILE.open("w") as f:
                f.write(ii.json())
            daemon.requestLoop()
        finally:
            LOCKFILE.unlink()
            RUNTIME_CONFIG.unlink()
