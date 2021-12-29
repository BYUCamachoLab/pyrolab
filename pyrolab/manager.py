# -*- coding: utf-8 -*-
#
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
from datetime import datetime
import importlib
import time
import threading
import multiprocessing
import logging
from multiprocessing import current_process
from multiprocessing.queues import Queue
from typing import TYPE_CHECKING, Dict, NamedTuple, Tuple, Type

from Pyro5.core import locate_ns

from pyrolab import RUNTIME_CONFIG
from pyrolab.nameserver import start_ns_loop
from pyrolab.configure import GlobalConfiguration, PyroLabConfiguration
from pyrolab.utils import bcolors

if TYPE_CHECKING:
    from Pyro5.core import URI

    from pyrolab.daemon import Daemon
    from pyrolab.service import Service
    from pyrolab.configure import NameServerConfiguration, DaemonConfiguration, ServiceConfiguration


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
    nameservercfg : dict
        The NameServerConfiguration as a dictionary (use ``to_dict()``) that 
        holds parameters necessary for constructing and running a server.
    msg_queue : multiprocessing.Queue
        A message queue. ResourceRunner listens for when ``None`` is placed
        in the queue, which is a sentinel value to shutdown the process.
    """
    def __init__(self, 
                 *args, 
                 name: str="",
                 nsconfig: NameServerConfiguration=None,
                 msg_queue: Queue=None, 
                 msg_polling: float=1.0,
                 **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if not name:
            self.name = multiprocessing.current_process().name
        else:
            self.name = f"{multiprocessing.current_process().name}: {name}"
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
            if msg is None:
                log.info(f"{self.name} recived KILL")
                self.KILL_SIGNAL = True

    def stay_alive(self):
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
        log.debug(f"{self.name}: Stay alive='{not self.KILL_SIGNAL}'")
        return not self.KILL_SIGNAL

    def run(self) -> None:
        """
        Creates and runs the child process.

        When the kill signal is received, gracefully shuts down and removes
        its registration from the nameserver.
        """
        log.info(f"Starting '{self.name}'")
        # TOPLEVEL_PID = os.environ["PYROLAB_TOPLEVEL_PID"]
        # print("Toplevel PID:", TOPLEVEL_PID)
    
        self.nsconfig.update_pyro_config()
        self.process_message_queue()
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
    info : ResourceInfo
        The ResourceInfo dataclass that holds parameters necessary for 
        constructing and running a server.
    msg_queue : multiprocessing.Queue
        A message queue. ResourceRunner only listens for when "None" is placed
        in the queue, which is a sentinel value to shutdown the process.
    """
    def __init__(self, 
                 *args, 
                 name: str="",
                 daemonconfig: DaemonConfiguration=None, 
                 serviceconfigs: Dict[ServiceConfiguration]=None,
                 msg_queue: Queue=None, 
                 msg_polling: float=1.0,
                 **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if not name:
            self.name = multiprocessing.current_process().name
        else:
            self.name = f"{multiprocessing.current_process().name}: {name}"
        self.msg_queue: Queue = msg_queue
        self.msg_polling = msg_polling
        self.daemonconfig = daemonconfig
        self.serviceconfigs = serviceconfigs
        self.KILL_SIGNAL = False

    def get_daemon(self) -> Type[Daemon]:
        """
        Returns the class object for the daemon given by the configuration.

        Returns
        -------
        Type[Daemon]
            The class of the referenced Daemon.
        """
        mod = importlib.import_module(self.daemonconfig.module)
        obj: Daemon = getattr(mod, self.daemonconfig.classname)
        return obj

    def get_service(self, serviceconfig: ServiceConfiguration) -> Type[Service]:
        """
        Gets the class object given by the ServiceConfiguration.

        Parameters
        ----------
        serviceconfig : ServiceConfiguration
            The ServiceConfiguration object that holds the information necessary to
            construct the Service.

        Returns
        -------
        Type[Service]
            The class of the referenced Service.
        """
        mod = importlib.import_module(serviceconfig.module)
        obj: Service = getattr(mod, serviceconfig.classname)
        
        obj.set_behavior(serviceconfig.instancemode)
        if serviceconfig.parameters:
            obj._autoconnect_params = serviceconfig.parameters

        return obj

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
        daemon = self.get_daemon()
        daemon = daemon()

        uris = {}
        for sname, sconfig in self.serviceconfigs.items():
            log.info(f"{self.name} registering service {sname}")
            service = self.get_service(sconfig)

            service = daemon.prepare_class(service)
            
            uri = daemon.register(service)
            uris[sname] = uri
        
        if self.daemonconfig.nameservers:
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
                log.info(f"{self.name} recived KILL")
                self.KILL_SIGNAL = True

    def stay_alive(self):
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
        log.info(f"Starting '{self.name}'")
        # TOPLEVEL_PID = os.environ["PYROLAB_TOPLEVEL_PID"]
        # print("Toplevel PID:", TOPLEVEL_PID)

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
                    log.debug("Daemon attempting to connect to nameserver")
                    ns = locate_ns(nscfg.host, nscfg.ns_port)
                    ns.register(sname, uris[sname], metadata={sinfo.description})
                except Exception as e:
                    log.critical(e)
                    raise e
        log.debug("Registration: success")

        for ns in self.daemonconfig.nameservers:
            nscfg = GLOBAL_CONFIG.nameservers[ns]
            ns = locate_ns(nscfg.host, nscfg.ns_port)
            ns.register(self.name, uris[self.name])

        # Start the request loop
        self.process_message_queue()
        log.debug(f"{self.name}: entering requestloop")
        daemon.requestLoop(loopCondition=self.stay_alive)

        # Cleanup
        log.info(f"Shutting down '{self.name}'")
        self._timer.cancel()
        for sname, sinfo in self.serviceconfigs.items():
            for ns in sinfo.nameservers:
                nscfg = GLOBAL_CONFIG.nameservers[ns]
                try:
                    ns = locate_ns(nscfg.host, nscfg.ns_port)
                    ns.remove(sname)
                except Exception as e:
                    log.error(e)


class ProcessGroup(NamedTuple):
    process: multiprocessing.Process
    msg_queue: Queue
    created: datetime


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
        raise RuntimeError("Cannot directly instantiate singleton, call ``instance()`` instead.")

    @classmethod
    def instance(cls):
        if current_process().name != 'MainProcess':
            raise Exception("ProcessManager should only be accessed by the main process.")
        if cls._instance is None:
            inst = cls.__new__(cls)
            inst.nameservers = {}
            inst.daemons = {}
            inst.GLOBAL_CONFIG = GlobalConfiguration.instance()
            cls._instance = inst
        return cls._instance

    def launch_nameserver(self, nameserver: str):
        """
        Launch a nameserver.
        """
        log.info(f'Launching server {nameserver}')
        nscfg = self.GLOBAL_CONFIG.get_nameserver_config(nameserver)
        messenger = multiprocessing.Queue()
        runner = NameServerRunner(
            name=nameserver,
            nsconfig=nscfg,
            msg_queue=messenger, 
            daemon=True
        )
        self.nameservers[nameserver] = NameServerProcessGroup(runner, messenger, datetime.now())
        runner.start()

    def get_nameserver_process(self, nameserver: str) -> NameServerProcessGroup:
        """
        Return the process group for a nameserver.
        """
        if nameserver in self.nameservers:
            return self.nameservers[nameserver]

    def launch_daemon(self, daemon: str):
        """
        Launch a daemon and all its associated services.
        """
        log.info(f'Launching daemon {daemon}')
        daemonconfig = self.GLOBAL_CONFIG.get_daemon_config(daemon)
        serviceconfigs = self.GLOBAL_CONFIG.get_service_configs_for_daemon(daemon)
        messenger = multiprocessing.Queue()
        runner = DaemonRunner(
            name=daemon,
            daemonconfig=daemonconfig,
            serviceconfigs=serviceconfigs,
            msg_queue=messenger, 
            daemon=True
        )
        self.daemons[daemon] = DaemonProcessGroup(runner, messenger, datetime.now())
        runner.start()

    def get_daemon_process(self, daemon: str) -> DaemonProcessGroup:
        """
        Return the process group for a daemon.
        """
        if daemon in self.daemons:
            return self.daemons[daemon]

    # def launch_all(self):
    #     """
    #     Launch all servers.
    #     """
    #     pass

    def shutdown_nameserver(self, nameserver: str) -> None:
        print(f"  Shutting down '{nameserver}'...", end="")
        group = self.nameservers[nameserver]
        polling = group.process.msg_polling
        group.msg_queue.put(None)
        time.sleep(polling)
        del self.nameservers[nameserver]
        print(f"{bcolors.OKGREEN}done{bcolors.ENDC}")

    def shutdown_daemon(self, daemon: str) -> None:
        print(f"  Shutting down '{daemon}'...", end="")
        group = self.daemons[daemon]
        polling = group.process.msg_polling
        group.msg_queue.put(None)
        time.sleep(polling)
        del self.daemons[daemon]
        print(f"{bcolors.OKGREEN}done{bcolors.ENDC}")

    def reload(self) -> bool:
        """
        Reload all servers.

        TODO: Implement this.
        """
        running_nameservers = list(self.nameservers.keys())
        running_daemons = list(self.daemons.keys())

        for name in running_nameservers:
            self.shutdown_nameserver(name)
        for name in running_daemons:
            self.shutdown_daemon(name)

        for name in running_nameservers:
            if name in self.GLOBAL_CONFIG.nameservers:
                self.launch_nameserver(name)
        for name in running_daemons:
            if name in self.GLOBAL_CONFIG.daemons:
                self.launch_daemon(name)

        return True

    def shutdown_all(self) -> None:
        for daemon in list(self.daemons.keys()):
            self.shutdown_daemon(daemon)
        for nameserver in list(self.nameservers.keys()):
            self.shutdown_nameserver(nameserver)

    # def wait_for_interrupt(self) -> None:
    #     try:
    #         while True:
    #             time.sleep(1)
    #     except KeyboardInterrupt:
    #         print("Shutting down all...")
    #         self.shutdown_all()
    #         print(f"{bcolors.OKGREEN}DONE{bcolors.ENDC}")
    #         raise
