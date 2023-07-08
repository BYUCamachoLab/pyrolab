# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Server Resources
----------------

The scripts used for putting up and taking down Daemons and Workers from the
multiprocessing module. Since child processes need to be able to import the
script containing the target function, the target functions are contained
within this module where no new processes are ever spawned. The prevents
the recursive creation of new processes as the module is imported.

Server Resource Manager
-----------------------

The server resource manager handles the putting up and taking down of Daemons
for various instruments. To increase computer speed and processing
capabilities in cases where multiple instruments are hosted from the same
computer, each instrument is created in its own Daemon using the
Python ``multiprocessing`` module.
"""

from __future__ import annotations

import logging
import multiprocessing
import threading
import time
from datetime import datetime
from multiprocessing import current_process
from multiprocessing.queues import Queue
from typing import TYPE_CHECKING, Dict, Tuple

from Pyro5.core import locate_ns

from pyrolab import RUNTIME_CONFIG
from pyrolab.configure import GlobalConfiguration, PyroLabConfiguration
from pyrolab.nameserver import start_ns_loop

if TYPE_CHECKING:
    from Pyro5.core import URI

    from pyrolab.configure import (
        DaemonConfiguration,
        NameServerConfiguration,
        ServiceConfiguration,
    )
    from pyrolab.server import Daemon


log = logging.getLogger(__name__)


class NameServerRunner(multiprocessing.Process):
    """
    A process for running nameservers using Python's ``multiprocessing``.

    Advantages of using a child Process include the fact that if a server
    dies or hangs up, the entire program doesn't stall or need to be restarted,
    just the process that contained the server. Thus errors can be handled
    and servers autonomously restarted and managed.

    Parameters
    ----------
    name : str
        The name of the nameserver being run.
    nsconfig : NameServerConfiguration
        The configuration for the nameserver.
    msg_queue : multiprocessing.Queue
        A message queue. ResourceRunner listens for when ``None`` is placed
        in the queue, which is a sentinel value to shutdown the process.
    msg_polling : float, optional
        The time in seconds between polling the message queue.
    """

    def __init__(
        self,
        *args,
        name: str = "",
        nsconfig: NameServerConfiguration = None,
        msg_queue: Queue = None,
        msg_polling: float = 1.0,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        if not name:
            raise ValueError("NameServerRunner requires a name")
        if not nsconfig:
            raise ValueError("NameServerRunner requires a NameServerConfiguration")
        if not msg_queue:
            raise ValueError("NameServerRunner requires a message queue")

        self.name = name
        self.msg_queue: Queue = msg_queue
        self.msg_polling = msg_polling
        self.nsconfig = nsconfig
        self.KILL_SIGNAL = False

    def process_message_queue(self) -> None:
        """
        A message handler.

        if the sentinel value ``None`` is placed in the message queue, sets
        a flag signifying a shutdown signal has been received.
        """
        self._timer = threading.Timer(self.msg_polling, self.process_message_queue)
        self._timer.daemon = True
        self._timer.start()

        if not self.msg_queue.empty():
            msg = self.msg_queue.get()
            log.debug(f"Message received: '{msg}'")
            if msg is None:
                log.info("KILL message received for nameserver '%s'", self.name)
                self.KILL_SIGNAL = True

    def stay_alive(self) -> bool:
        """
        A callback listener; if the sentinel value ``None`` is placed in the
        message queue, returns True signifying a shutdown signal has been
        received.

        This function is called by the Daemon's ``requestLoop()``.

        Returns
        -------
        bool
            True if shutdown signal received, False otherwise.
        """
        log.debug(f"Stay alive='{not self.KILL_SIGNAL}'")
        return not self.KILL_SIGNAL

    def run(self) -> None:
        """
        Creates and runs the child process.

        When the kill signal is received, gracefully shuts down and removes
        its registration from the nameserver.
        """
        log.info("Starting nameserver '%s'", self.name)

        # Configure the Pyro5 environment
        self.nsconfig.update_pyro_config()
        # Start the thread that checks for messages
        self.process_message_queue()
        # Begin looping
        start_ns_loop(self.nsconfig, loop_condition=self.stay_alive)


class DaemonRunner(multiprocessing.Process):
    """
    A process for running server daemons using Python's ``multiprocessing``.

    Advantages of using a ResourceRunner include the fact that if a server
    dies or hangs up, the entire program doesn't stall or need to be restarted,
    just the process that contained the server. Thus errors can be handled
    and servers autonomously restarted and managed.

    Other advantages should include speed; splitting servers across processors
    means that resource-heavy instruments won't bog down adjacent instruments.

    Parameters
    ----------
    name : str
        The name of the daemon being run.
    daemonconfig : DaemonConfiguration
        The configuration for the daemon.
    serviceconfigs : Dict[str, ServiceConfiguration]
        The configuration for the services belonging to the given daemon.
    msg_queue : multiprocessing.Queue
        A message queue. ResourceRunner listens for when "None" is placed
        in the queue, which is a sentinel value to shutdown the process.
    msg_polling : float, optional
        The time in seconds between polling the message queue.
    """

    def __init__(
        self,
        *args,
        name: str = "",
        daemonconfig: DaemonConfiguration = None,
        serviceconfigs: Dict[str, ServiceConfiguration] = None,
        msg_queue: Queue = None,
        msg_polling: float = 1.0,
        **kwargs,
    ) -> None:
        log.debug("Building DaemonRunner")
        # TODO: Add log statements before raising exceptions
        super().__init__(*args, **kwargs)
        if not name:
            raise ValueError("DaemonRunner requires a name")
        if not daemonconfig:
            raise ValueError("DaemonRunner requires a DaemonConfiguration")
        if not serviceconfigs:
            log.critical(
                f"No service configurations for daemon '{name}', did you intend to register services?"
            )
            raise ValueError("DaemonRunner requires ServiceConfigurations")
        if not msg_queue:
            raise ValueError("DaemonRunner requires a message queue")

        self.name = name
        self.msg_queue: Queue = msg_queue
        self.msg_polling = msg_polling
        self.daemonconfig = daemonconfig
        self.serviceconfigs = serviceconfigs
        self.KILL_SIGNAL = False

    def setup_daemon(self) -> Tuple[Daemon, Dict[str, URI]]:
        """
        Locates and loads the Daemon class, adds Pyro's ``behavior``, and
        registers the hosted object with the Daemon.

        Returns
        -------
        daemon, uri
            The instantiated Daemon object and the URI for the hosted object,
            to be registered with the nameserver.
        """
        daemon = self.daemonconfig._get_daemon()
        daemon = daemon()

        uris = {}
        for sname, sconfig in self.serviceconfigs.items():
            log.info(f"Registering service '{sname}'")
            service = sconfig._get_service()

            log.debug("Getting service uri")
            uri = daemon.register(service)
            uris[sname] = uri
            log.info("URI for '%s' = %s", sname, uri)

        if self.daemonconfig.nameservers:
            log.debug("Self-registering daemon")
            uri = daemon.register(daemon)
            uris[self.name] = uri

        return daemon, uris

    def process_message_queue(self) -> None:
        """
        A message handler.

        if the sentinel value ``None`` is placed in the message queue, sets
        a flag signifying a shutdown signal has been received.
        """
        self._timer = threading.Timer(self.msg_polling, self.process_message_queue)
        self._timer.daemon = True
        self._timer.start()

        if not self.msg_queue.empty():
            msg = self.msg_queue.get()
            if msg is None:
                log.info("KILL message received for daemon '%s'", self.name)
                self.KILL_SIGNAL = True

    def stay_alive(self) -> bool:
        """
        A callback listener; if the sentinel value ``None`` is placed in the
        message queue, returns True signifying a shutdown signal has been
        received.

        This function is called by the Daemon's ``requestLoop()``.

        Returns
        -------
        bool
            True if shutdown signal received, False otherwise.
        """
        return not self.KILL_SIGNAL

    def run(self) -> None:
        """
        Creates and runs the child process.

        When the kill signal is received, gracefully shuts down and removes
        its registration from the nameserver.
        """
        log.info("Starting daemon '%s'", self.name)

        # Set Pyro5 settings for daemon
        self.daemonconfig.update_pyro_config()
        daemon, uris = self.setup_daemon()

        GLOBAL_CONFIG = PyroLabConfiguration.from_file(RUNTIME_CONFIG)

        # Register all services with the nameserver
        log.debug("Registering services with nameserver")
        for sname, sinfo in self.serviceconfigs.items():
            for ns in sinfo.nameservers:
                nscfg = GLOBAL_CONFIG.nameservers[ns]
                try:
                    log.debug(
                        f"Attempting to register '{sname}' with nameserver '{ns}' at {nscfg.host}:{nscfg.ns_port}"
                    )
                    ns = locate_ns(nscfg.host, nscfg.ns_port)
                    ns.register(sname, uris[sname], metadata={sinfo.description})
                except Exception as e:
                    log.exception(e)
                    raise e
        log.debug("All registrations completed")

        for ns in self.daemonconfig.nameservers:
            nscfg = GLOBAL_CONFIG.nameservers[ns]
            ns = locate_ns(nscfg.host, nscfg.ns_port)
            description = (
                f"Daemon for {', '.join([str(sname) for sname in self.serviceconfigs])}"
            )
            ns.register(self.name, uris[self.name], metadata={description})

        # Start the request loop
        self.process_message_queue()
        log.debug("entering request loop for '%s'", self.name)
        daemon.requestLoop(loopCondition=self.stay_alive)
        log.debug("requestloop exited for '%s'", self.name)

        # Cleanup
        log.info("Daemon '%s' is shutting down.", self.name)
        self._timer.cancel()
        for sname, sinfo in self.serviceconfigs.items():
            for ns in sinfo.nameservers:
                nscfg = GLOBAL_CONFIG.nameservers[ns]
                try:
                    ns = locate_ns(nscfg.host, nscfg.ns_port)
                    ns.remove(sname)
                except Exception as e:
                    log.exception(e)
        for ns in self.daemonconfig.nameservers:
            nscfg = GLOBAL_CONFIG.nameservers[ns]
            try:
                ns = locate_ns(nscfg.host, nscfg.ns_port)
                ns.remove(self.name)
            except Exception as e:
                log.exception(e)


class ProcessGroup:
    def __init__(
        self, process: multiprocessing.Process, msg_queue: Queue, created: datetime
    ) -> None:
        self.process = process
        self.msg_queue = msg_queue
        self.created = created


class NameServerProcessGroup(ProcessGroup):
    pass


class DaemonProcessGroup(ProcessGroup):
    pass


class ProcessManager:
    """
    A manager class for running a set of PyroLab processes.

    ProcessManager is a singleton. Access the global object by calling
    :py:func:`instance`. Only the main process can access the ProcessManager.
    """

    _instance = None
    nameservers: Dict[str, NameServerProcessGroup] = {}
    daemons: Dict[str, DaemonProcessGroup] = {}

    def __init__(self) -> None:
        raise RuntimeError(
            "Cannot directly instantiate singleton, call ``instance()`` instead."
        )

    @classmethod
    def instance(cls) -> "ProcessManager":
        """
        Get the singleton instance of the ProcessManager.

        Only the main process can access the ProcessManager.

        Returns
        -------
        ProcessManager
            The singleton instance of the ProcessManager.

        Raises
        ------
        RuntimeError
            If the requesting process is not the main process.
        """
        # TODO: Do we want to change it so the GlobalConfiguration object is
        # injected, instead of "gotten" by the ProcessManager itself?
        log.debug("ProcessManager instance requested")
        if current_process().name != "MainProcess":
            log.critical("ProcessManager instance requested from non-main process")
            raise Exception(
                "ProcessManager should only be accessed by the main process."
            )
        if cls._instance is None:
            log.debug("ProcessManager instance did not exist, created")
            inst = cls.__new__(cls)
            inst.nameservers = {}
            inst.daemons = {}
            inst.GLOBAL_CONFIG = GlobalConfiguration.instance()
            inst.start_checkup_timer()
            cls._instance = inst
        return cls._instance

    def start_checkup_timer(self, duration: float = 30.0) -> None:
        """
        Starts a timer to check up on the processes every n seconds (default 30).
        """
        self._timer = threading.Timer(duration, self.checkup)
        self._timer.daemon = True
        log.debug("Starting checkup timer")
        self._timer.start()

    def stop_checkup_timer(self) -> None:
        """
        Stops the checkup timer.
        """
        log.debug("Stopping checkup timer")
        if hasattr(self, "_timer"):
            self._timer.cancel()

    def launch_nameserver(self, nameserver: str) -> bool:
        """
        Launch a nameserver.
        """
        log.info("Manager attempting to launch server '%s'", nameserver)
        nscfg = self.GLOBAL_CONFIG.get_nameserver_config(nameserver)
        messenger = multiprocessing.Queue()
        runner = NameServerRunner(
            name=nameserver, nsconfig=nscfg, msg_queue=messenger, daemon=True
        )
        self.nameservers[nameserver] = NameServerProcessGroup(
            runner, messenger, datetime.now()
        )
        runner.start()
        return True

    def get_nameserver_process_info(self, nameserver: str) -> Dict[str, str]:
        """
        Gets info on a nameserver process.

        Parameters
        ----------
        nameserver : str
            The name of the nameserver.

        Returns
        -------
        Dict[str, str]
            A dictionary of information about the nameserver. Keys are:
            ``created``, ``status``, ``uri``.
        """
        log.debug("Entering get_nameserver_process_info()")
        if nameserver in self.nameservers:
            pgroup = self.nameservers[nameserver]
            if pgroup.process.is_alive():
                status = running_time_human_readable(pgroup.created)
            else:
                status = "Died"
            return {
                "created": pgroup.created.strftime("%Y-%m-%d %H:%M:%S"),
                "status": status,
                "uri": "",
            }
        else:
            return {
                "created": "",
                "status": "Stopped",
                "uri": "",
            }

    def launch_daemon(self, daemon: str) -> bool:
        """
        Launch a daemon and all its associated services.
        """
        log.info("Manager attempting to launch daemon '%s'", daemon)
        daemonconfig = self.GLOBAL_CONFIG.get_daemon_config(daemon)
        serviceconfigs = self.GLOBAL_CONFIG.get_service_configs_for_daemon(daemon)
        messenger = multiprocessing.Queue()
        runner = DaemonRunner(
            name=daemon,
            daemonconfig=daemonconfig,
            serviceconfigs=serviceconfigs,
            msg_queue=messenger,
            daemon=True,
        )
        self.daemons[daemon] = DaemonProcessGroup(runner, messenger, datetime.now())
        runner.start()
        return True

    def get_daemon_process_info(self, daemon: str) -> Dict[str, str]:
        """
        Return the process group for a daemon.
        """
        log.debug("Entering get_daemon_process_info()")
        if daemon in self.daemons:
            pgroup = self.daemons[daemon]
            if pgroup.process.is_alive():
                status = running_time_human_readable(pgroup.created)
            else:
                status = "Died"
            return {
                "created": pgroup.created.strftime("%Y-%m-%d %H:%M:%S"),
                "status": status,
                "uri": "",
            }
        else:
            return {
                "created": "",
                "status": "Stopped",
                "uri": "",
            }

    def checkup(self, continuous: bool = True) -> None:
        """
        Checkup the processes.
        """
        log.debug("Entering checkup()")

        for ns in list(self.nameservers.keys()):
            if not self.nameservers[ns].process.is_alive():
                log.warning(f"Nameserver '{ns}' died, attempting to restart process.")
                try:
                    self.nameservers[ns].process.join()
                    log.debug(f"Nameserver '{ns}' joined processes.")
                    del self.nameservers[ns]
                    self.launch_nameserver(ns)
                except Exception as e:
                    log.exception(e)
        for daemon in list(self.daemons.keys()):
            if not self.daemons[daemon].process.is_alive():
                log.warning(f"Daemon '{daemon}' died, attempting to restart process.")
                try:
                    self.daemons[daemon].process.join()
                    log.debug(f"Daemon '{daemon}' joined processes.")
                    del self.daemons[daemon]
                    self.launch_daemon(daemon)
                except Exception as e:
                    log.exception(e)

        if continuous:
            self.start_checkup_timer()

    def shutdown_nameserver(self, nameserver: str) -> bool:
        log.info(f"Sending KILL message to nameserver '{nameserver}'")
        group = self.nameservers.pop(nameserver)
        polling = group.process.msg_polling
        group.msg_queue.put(None)
        time.sleep(2 * polling)
        return True

    def shutdown_daemon(self, daemon: str) -> bool:
        log.info(f"Sending KILL message to daemon '{daemon}'")
        group = self.daemons.pop(daemon)
        polling = group.process.msg_polling
        group.msg_queue.put(None)
        time.sleep(2 * polling)
        return True

    def reload(self) -> bool:
        """
        Reload all entities.
        """
        log.info("Reloading all running entities.")
        running_nameservers = list(self.nameservers.keys())
        running_daemons = list(self.daemons.keys())

        self.stop_checkup_timer()

        for name in running_daemons:
            self.shutdown_daemon(name)
        for name in running_nameservers:
            self.shutdown_nameserver(name)

        for name in running_nameservers:
            if name in self.GLOBAL_CONFIG.config.nameservers:
                self.launch_nameserver(name)
        for name in running_daemons:
            if name in self.GLOBAL_CONFIG.config.daemons:
                self.launch_daemon(name)

        self.start_checkup_timer()

        return True

    def shutdown_all(self) -> None:
        """
        Shutdown all entities.
        """
        log.info("Shutting down all running entities.")

        self.stop_checkup_timer()

        for daemon in list(self.daemons.keys()):
            self.shutdown_daemon(daemon)
        for nameserver in list(self.nameservers.keys()):
            self.shutdown_nameserver(nameserver)

        log.info("All running entities successfully shut down.")


def running_time_human_readable(start: datetime, end: datetime = None) -> str:
    """
    Return the time delta of two times (or one and now) in plain English.

    Parameters
    ----------
    start : datetime
        The start time.
    end : datetime, optional
        The end time. Defaults to now.

    Returns
    -------
    str
        The time delta in plain English.
    """
    if end:
        delta = end - start
    else:
        delta = datetime.now() - start
    if delta.days > 0:
        return f"Up {delta.days} days"
    elif delta.seconds > 3600:
        return f"Up {delta.seconds // 3600} hours"
    elif delta.seconds > 120:
        return f"Up {delta.seconds // 60} minutes"
    elif delta.seconds > 60:
        return f"Up 1 minute"
    else:
        return f"Up {delta.seconds} seconds"
