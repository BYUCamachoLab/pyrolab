# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Server
------

Wrapped server functions that references PyroLab configuration settings.
"""

import atexit
import logging
from multiprocessing import current_process

import Pyro5

from pyrolab.server.locker import Lockable
from pyrolab.server.resourcemanager import ResourceManager
from pyrolab.utils.network import get_ip


log = logging.getLogger("pyrolab.server")


class Daemon(Pyro5.server.Daemon):
    pass


class LockableDaemon(Daemon):
    """
    A LockableDaemon only supports the registration of a single object per
    daemon.
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.__HAS_OBJECT = False
        self.register

    def register(self, *args, **kwargs):
        if self.__HAS_OBJECT:
            raise Exception("Daemon already contains an object.")
        else:
            self.__HAS_OBJECT = True
            return super().register(*args, **kwargs)

    def unregister(self, *args, **kwargs):
        self.__HAS_OBJECT = False
        return super().unregister(*args, **kwargs)

    def validateHandshake(self, conn, data):
        """
        Determines whether a handshake can be allowed for
        ``SingleObjectDaemon``s by checking the lock status of the enclosed 
        object.

        Raises
        ------
        Exception
            If the object is locked, connection will be refused.
        """
        # If an instance doesn't exist, it can't be locked.
        if len(self._pyroInstances.values()) > 0:
            # If it exists, it'll be the only object in a SingleObjectDaemon
            obj = list(self._pyroInstances.values())[0]
            if issubclass(obj.__class__, Lockable):
                if obj.islocked():
                    raise Exception("Pyro object is locked, refusing connection.")
        return "hello"

    def clientDisconnect(self, conn):
        """
        Releases any locked services in the event of a client disconnect.

        Parameters
        ----------
        conn : SocketConnection
            The SocketConnection object that was disconnected.
        """
        if len(self._pyroInstances.values()) > 0:
            # If it exists, it'll be the only object in a SingleObjectDaemon
            obj = list(self._pyroInstances.values())[0]
            if issubclass(obj.__class__, Lockable):
                if obj.islocked():
                    print("Client connection closed, releasing lock.")
                    obj.release()


class AutoconnectLockableDaemon(LockableDaemon):
    """
    Daemon that adds autoconnect parameters to the hosted object.
    """
    def _getInstance(self, clazz, conn):
        instance = super()._getInstance(clazz, conn)
        instance._autoconnect_params = self.connect_params
        return instance

    def register(self, *args, connect_params={}, **kwargs):
        self.connect_params = connect_params
        return super().register(*args, **kwargs)

    def unregister(self, *args, **kwargs):
        self.connect_params = {}
        return super().unregister(*args, **kwargs)


def start_default_public_server(ns_host: str, ns_port: int) -> None:
    """
    Given the nameserver host and port, gets the public ip address of the
    local machine and hosts all known resources, registering them with the
    nameserver.

    Parameters
    ----------
    ns_host : str
        The hostname of the nameserver.
    ns_port : int
        The port of the nameserver.
    """
    manager = ResourceManager.instance()
    manager.update_host(get_ip())
    manager.update_ns(ns_host=ns_host, ns_port=ns_port)
    manager.launch_all()

def start_default_local_server(ns_host: str="localhost", ns_port: int=9090) -> None:
    """
    Given the nameserver host and port, hosts all known resources on localhost, 
    registering them with the nameserver.

    Parameters
    ----------
    ns_host : str, optional
        The hostname of the nameserver (default "localhost").
    ns_port : int, optional
        The port of the nameserver (default 9090).
    """
    manager = ResourceManager.instance()
    manager.update_host("localhost")
    manager.update_ns(ns_host=ns_host, ns_port=ns_port)
    manager.launch_all()

@atexit.register
def shutdown_on_exit():
    if current_process().name == 'MainProcess':
        log.info("Shutting down all processes in ResourceManager.")
        manager = ResourceManager.instance()
        manager.shutdown_all()
