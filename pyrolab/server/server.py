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

import logging
import Pyro5

from pyrolab.server.configure import ServerConfiguration, srv_profile as profile
from pyrolab.server.locker import Lockable
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


def create_public_configuration():
    name = 'auto'
    cfg = ServerConfiguration(
        host=get_ip()
    )
    