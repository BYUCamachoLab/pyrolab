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

from __future__ import annotations

import getpass
import inspect
import logging
from typing import TYPE_CHECKING, Callable, Optional, Type

import Pyro5
from Pyro5.core import URI
from Pyro5.server import behavior, expose, oneway, serve

if TYPE_CHECKING:
    from Pyro5.socketutil import SocketConnection

    from pyrolab.drivers import Instrument
    from pyrolab.service import Service


log = logging.getLogger(__name__)


def change_behavior(cls: Type[Instrument], instance_mode: str="session", instance_creator: Optional[Callable]=None):
    """
    Dynamically add a behavior to a class.

    Equivalent to using the ``behavior`` decorator on the class, but can 
    be used dynamically during runtime. Services that specify some default 
    behavior in the source code can be overridden using this function.

    .. warning::
       This function modifies the behavior of the class in place! It does 
       not returning a new class object.

    Parameters
    ----------
    cls : class
        The class to be change the behavior of.
    instance_mode : str
        One of "session", "single", or "percall" (see manual for differences).
    instance_creator : callable
        A callable that creates a new instance of the class (see manual for
        more details).

    Raises
    ------
    ValueError
        If the ``instance_mode`` is not one of "session", "single", or "percall".
    SyntaxError
        If ``instance_mode`` is not a string, or is missing.
    TypeError
        If the first argument is not a class, or ``instance_creator`` is not a callable.
    """
    if not isinstance(instance_mode, str):
        raise SyntaxError("behavior decorator is missing argument(s)")
    if not inspect.isclass(cls):
        raise TypeError("add_behavior can only be used on a class")
    if instance_mode not in ("single", "session", "percall"):
        raise ValueError("invalid instance mode: " + instance_mode)
    if instance_creator and not callable(instance_creator):
        raise TypeError("instance_creator must be a callable")
    cls._pyroInstancing = (instance_mode, instance_creator)


@expose
class Lockable:
    """
    The Lockable instrument mixin. Only works with LockableDaemon.
    
    Rejects new connections at the Daemon level when locked. Daemon stores the 
    user who locked the device for reference.
    """
    def lock(self, user: str="") -> bool:
        """
        Locks access to the object's attributes.

        Parameters
        ----------
        user : str, optional
            The user who has locked the device. Useful when a device is locked
            and another user wants to know who is using it.
        """
        daemon = getattr(self, "_pyroDaemon", None)
        if daemon:
            return daemon._lock(self._pyroId, daemon._last_requestor, user)
        return True

    def unlock(self) -> bool:
        """
        Releases the lock on the object.
        """
        daemon = getattr(self, "_pyroDaemon", None)
        if daemon:
            return daemon._release(self._pyroId)
        return True

    def islocked(self) -> bool:
        """
        Returns the status of the lock.

        Returns
        -------
        bool
            True if the lock is engaged, False otherwise.
        """
        daemon = getattr(self, "_pyroDaemon", None)
        if daemon:
            return daemon._islocked(self._pyroId)
        return False


class Daemon(Pyro5.server.Daemon):
    """
    The PyroLab server daemon. This class is based on the Pyro5.server.Daemon.

    Parameters
    ----------
    host : str or None 
        The hostname or IP address to bind the server on. Default is None which 
        means it uses the configured default (which is localhost). It is 
        necessary to set this argument to a visible hostname or ip address, if 
        you want to access the daemon from other machines.
    port : int, optional
        Port to bind the server on. Defaults to 0, which means to pick a random 
        port.
    unixsocket : str, optional
        The name of a Unix domain socket to use instead of a TCP/IP socket. 
        Default is None (don’t use).
    nathost : str, optional
        hostname to use in published addresses (useful when running behind a 
        NAT firewall/router). Default is None which means to just use the 
        normal host. For more details about NAT, see Pyro behind a NAT 
        router/firewall.
    natport : int, optional
        Port to use in published addresses (useful when running behind a NAT 
        firewall/router). If you use 0 here, Pyro will replace the NAT-port by 
        the internal port number to facilitate one-to-one NAT port mappings.
    interface : DaemonObject, optional
        Optional alternative daemon object implementation (that provides the 
        Pyro API of the daemon itself).
    connected_socket : SocketConnection, optional
        Pptional existing socket connection to use instead of creating a new 
        server socket.
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    @staticmethod
    def prepare_class(cls) -> Type[Service]:
        """
        Performs any actions on the class required for the given Daemon.

        Some classes require mixins to be added in order for certain 
        functionality to work. When the ProcessManager prepares to run a Daemon,
        the child process will call this method on the class before registering
        the class.

        Parameters
        ----------
        cls : class
            The class to prepare.
        
        Returns
        -------
        class
            The prepared class.
        """
        return cls


class LockableDaemon(Daemon):
    """
    A LockableDaemon supports lockable resources.

    Lockable resources are objects that can be locked by a client. This is
    useful for preventing multiple clients from accessing the same resource
    simultaneously. The lock can be released manually, or is automatically
    released when the client disconnects.

    Only objects with instance behavior "single" can be locked.

    Parameters
    ----------
    host : str or None 
        The hostname or IP address to bind the server on. Default is None which 
        means it uses the configured default (which is localhost). It is 
        necessary to set this argument to a visible hostname or ip address, if 
        you want to access the daemon from other machines.
    port : int, optional
        Port to bind the server on. Defaults to 0, which means to pick a random 
        port.
    unixsocket : str, optional
        The name of a Unix domain socket to use instead of a TCP/IP socket. 
        Default is None (don’t use).
    nathost : str, optional
        hostname to use in published addresses (useful when running behind a 
        NAT firewall/router). Default is None which means to just use the 
        normal host. For more details about NAT, see Pyro behind a NAT 
        router/firewall.
    natport : int, optional
        Port to use in published addresses (useful when running behind a NAT 
        firewall/router). If you use 0 here, Pyro will replace the NAT-port by 
        the internal port number to facilitate one-to-one NAT port mappings.
    interface : DaemonObject, optional
        Optional alternative daemon object implementation (that provides the 
        Pyro API of the daemon itself).
    connected_socket : SocketConnection, optional
        Pptional existing socket connection to use instead of creating a new 
        server socket.
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.locked_instances = {}

    @staticmethod
    def prepare_class(cls) -> Type[Service]:
        """
        Dynamically create a new class that is also based on Lockable.

        Parameters
        ----------
        cls : class
            The class to be used as a template while dynamically creating a new
            class.
        
        Returns
        -------
        class
            A subclass that inherits from the original class and ``Lockable``.
        """
        DynamicLockable = type(
            cls.__name__ + "Lockable",
            (cls, Lockable, ),
            {}
        )
        return DynamicLockable

    def _lock(self, pyroId: str, conn: SocketConnection, user: str=getpass.getuser()) -> bool:
        """
        Logs a "lock" action on a Pyro object.
        
        LockableDaemon tracks which connection owns the lock over a given Pyro
        object.

        Parameters
        ----------
        pyroId : str
            The pyroId of the Pyro object.
        conn : SocketConnection
            The socket connection with the client that owns the lock.
        user : str, optional
            The user who has locked the device. Useful when a device is locked
            by a user and another user wants to know who is using it.
            By default, this is the username of the computer account that
            obtained the lock.

        Returns
        -------
        bool
            A success status flag.
        """
        if pyroId not in self.locked_instances:
            self.locked_instances[pyroId] = (conn, user)
        return True

    def _release(self, pyroId: str) -> bool:
        """
        Logs a "lock release" action on a Pyro object.

        LockableDaemon tracks which connection owns the lock over a given Pyro
        object. In the case of a release action, it does not matter which
        connection makes the release; only lock owners can even access the 
        release attribute.

        Parameters
        ----------
        pyroId : str
            The object to be released.

        Returns
        -------
        bool
            A success status flag. False if the instance wasn't locked to begin
            with.
        """
        removed = self.locked_instances.pop(pyroId, None)
        return True if removed else False

    def _islocked(self, pyroId: str) -> bool:
        """
        Checks if a Pyro object is locked.

        Parameters
        ----------
        pyroId : str
            The pyroId of the object to check.

        Returns
        -------
        bool
            A success status flag.
        """
        return True if (pyroId in self.locked_instances) else False

    @expose
    def release(self, uri: str) -> str:
        """
        Provides a way to force unlock a resource via the Daemon itself.

        The Daemon must itself be registered to a Daemon and be assigned a URI.
        That Daemon can very well be itself.

        Parameters
        ----------
        uri : str
            The Pyro URI of the object to be unlocked.

        Returns
        -------
        result : bool
            True if the resource was successfully released, False otherwise.

        Raises
        ------
        Pyro5.errors.PyroError
            If the URI is invalid.
        """
        objId = URI(uri).object
        obj = self.objectsById[objId]

        # Only matters when instance mode is "single".
        instance = self._pyroInstances.get(obj)
        if instance:
            return instance.release()
        else:
            return True

    @expose
    def ping(self) -> str:
        """
        Returns a string to indicate that the Daemon is alive.

        Returns
        -------
        result : str
            A string to indicate that the Daemon is alive.
        """
        return "pong"

    def _getInstance(self, clazz, conn):
        """
        Find or create a new instance of the class.
        
        If an instance already exists, but is locked, an exception is raised.
        
        Parameters
        ----------
        clazz
            The Pyro object being accessed.
        conn
            The connection object the request is being made from.
        
        Returns
        -------
        instance : clazz
            The instance of the Pyro object being accessed.
        
        Raises
        ------
        Exception
            If an instance exists but is locked by a different connection.
        """
        self._last_requestor = conn
        obj = super()._getInstance(clazz, conn)
        if issubclass(obj.__class__, Lockable):
            lock_owner, username = self.locked_instances.get(obj._pyroId, (None, ""))
            if lock_owner is None or lock_owner == conn:
                return obj
            if lock_owner != conn:
                raise Exception(f"Pyro object is locked (by '{username or lock_owner}').")

    def clientDisconnect(self, conn):
        """
        Automatically releases any locked resources in the event of a client 
        disconnect.

        Parameters
        ----------
        conn : SocketConnection
            The SocketConnection object that was disconnected.
        """
        for pyroId in list(self.locked_instances.keys()):
            owner, username = self.locked_instances[pyroId][0]
            if conn == owner:
                del self.locked_instances[pyroId]
            log.info(f"Client connection closed, releasing lock owned by '{username}'.")
