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
import importlib
import time
import threading
import multiprocessing
import logging
from multiprocessing import current_process
from multiprocessing.queues import Queue
from typing import TYPE_CHECKING, Any, Dict, Tuple, Type

from Pyro5.core import locate_ns

from pyrolab.configure import (
    load_ns_configs, 
    load_server_configs, 
    load_service_configs, 
    get_services_for_server,
)
from pyrolab.service import Service

if TYPE_CHECKING:
    from Pyro5.core import URI

    from pyrolab.daemon import Daemon, DaemonConfiguration
    from pyrolab.service import ServiceInfo


log = logging.getLogger(__name__)


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
                 serverconfig: DaemonConfiguration=None, 
                 serviceinfos: Dict[str, ServiceInfo]=None,
                 msg_queue: Queue=None, 
                 msg_polling: float=1.0,
                 **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.msg_queue: Queue = msg_queue
        self.msg_polling = msg_polling
        self.serverconfig = serverconfig
        self.serviceinfos = serviceinfos
        self.KILL_SIGNAL = False

    def get_daemon(self) -> Type[Daemon]:
        """
        Returns the object for the daemon in PyroLab referenced by 
        ResourceInfo.

        Returns
        -------
        Type[Daemon]
            The class of the referenced Daemon.
        """
        mod = importlib.import_module(self.serverconfig.module)
        obj: Daemon = getattr(mod, self.serverconfig.classname)
        return obj

    def get_service(self, serviceinfo: ServiceInfo) -> Type[Service]:
        """
        Gets the object given the ServiceInfo.

        Parameters
        ----------
        serviceinfo : ServiceInfo
            The ServiceInfo object that holds the information necessary to
            construct the Service.

        Returns
        -------
        Type[Service]
            The class of the referenced Service.
        """
        mod = importlib.import_module(serviceinfo.module)
        obj: Service = getattr(mod, serviceinfo.classname)
        
        obj.set_behavior(serviceinfo.instancemode)
        if serviceinfo.parameters:
            obj._autoconnect_params = {k:v for x in serviceinfo.parameters for k, v in x.items()}

        return obj

    def setup_daemon(self) -> Tuple[Daemon, Dict[str, URI]]:
        """
        Locates and loads the Daemon class, adds Pyro's ``behavior``, and 
        registers the hosted object with the Daemon.

        Returns
        -------
        daemon, uri
            The Daemon object and the URI for the hosted object, to be 
            registered with the nameserver.
        """
        daemon = self.get_daemon()
        daemon = daemon()
        uris = {}
        for servicename, serviceinfo in self.serviceinfos.items():
            log.info(f"{multiprocessing.current_process().name} registering service {servicename}")
            service = self.get_service(serviceinfo)

            service = daemon.prepare_class(service)
            
            uri = daemon.register(service)
            uris[servicename] = uri
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
                log.info(f"{multiprocessing.current_process().name} recived KILL")
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
        name = multiprocessing.current_process().name
        log.info(f"Starting '{name}'")

        self.serverconfig.update_pyro_config()
        daemon, uris = self.setup_daemon()

        nscfgs = load_ns_configs()
        for servicename, serviceinfo in self.serviceinfos.items():
            for ns in serviceinfo.nameservers:
                nscfg = nscfgs[ns]
                ns = locate_ns(nscfg.host, nscfg.ns_port)
                ns.register(serviceinfo.name, uris[servicename], metadata=serviceinfo.description)

        self.process_message_queue()
        daemon.requestLoop(loopCondition=self.stay_alive)

        log.info(f"Shutting down '{name}'")
        self._timer.cancel()
        for servicename, serviceinfo in self.serviceinfos.items():
            for ns in serviceinfo.nameservers:
                nscfg = nscfgs[ns]
                ns = locate_ns(nscfg.host, nscfg.ns_port)
                ns.remove(servicename)


class DaemonManager:
    _instance = None

    def __init__(self) -> None:
        raise RuntimeError("Call ``instance()`` instead.")

    @classmethod
    def instance(cls):
        if current_process().name != 'MainProcess':
            raise Exception("DaemonManager should only be accessed by the main process.")
        if cls._instance is None:
            inst = cls.__new__(cls)
            inst.processes: Dict[str, DaemonRunner] = {}
            inst.messengers: Dict[str, Queue] = {}
            cls._instance = inst
        return cls._instance

    def launch(self, servername: str):
        """
        Launch a server.
        """
        print(servername)
        serverconfig = load_server_configs()[servername]
        serviceinfos = get_services_for_server(servername)
        print(serviceinfos, len(serviceinfos))
        messenger = multiprocessing.Queue()
        runner = DaemonRunner(serverconfig=serverconfig, serviceinfos=serviceinfos, msg_queue=messenger, daemon=True)
        self.processes[servername] = runner
        self.messengers[servername] = messenger
        runner.start()

    # def launch_all(self):
    #     """
    #     Launch all servers.
    #     """
    #     pass

    def shutdown(self, servername: str) -> None:
        polling = self.processes[servername].msg_polling
        self.messengers[servername].put(None)
        time.sleep(polling)
        del self.processes[servername]
        del self.messengers[servername]

    def shutdown_all(self) -> None:
        for servername in list(self.processes.keys()):
            self.shutdown(servername)

    def wait_for_interrupt(self) -> None:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown_all()
            raise
