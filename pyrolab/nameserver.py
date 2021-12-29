# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Nameserver
----------

Wrapped nameserver functions that references PyroLab configuration settings.
"""

import sys
import socket
import logging
from typing import Callable

from Pyro5.nameserver import NameServerDaemon, BroadcastServer, start_ns
from pyrolab.configure import NameServerConfiguration

from pyrolab import PYROLAB_DATA_DIR


log = logging.getLogger(__name__)


NAMESERVER_DATA_DIR = PYROLAB_DATA_DIR / "nameserver" / "data"
NAMESERVER_DATA_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_FILE = NAMESERVER_DATA_DIR / "storage"


# # Inheriting from the Nameserver
# class NameServer(Pyro5.nameserver.NameServer):
#     """
#     PyroLab specific NameServer with custom functionality including the ability
#     to reject duplicate registration names.
#     """
#     pass


def start_ns_loop(cfg: NameServerConfiguration, loop_condition: Callable=lambda: True) -> None:
    """
    Utility function that starts a new NameServer and enters its requestloop.

    This function is a reimplemntation of the ``Pyro5.nameserver.start_ns_loop``
    that allows for a loop condition to kill the loop. Alternatively, the loop 
    can be shut down using ``ctrl+c``.

    Parameters
    ----------
    cfg : NameserverConfiguration
        The configuration object for the nameserver.
    loop_condition : callable, optional
        A callable that returns a boolean value. If the value is True, the loop
        will continue. If the value is False, the loop will stop. Defaults to
        ``lambda: True``.
    """
    # Parameters from the original function
    host = cfg.host
    port = cfg.ns_port
    unixsocket = None
    nathost = None
    natport = None
    enableBroadcast = cfg.broadcast
    bchost = cfg.ns_bchost
    bcport = cfg.ns_bcport
    storage = cfg.get_storage_location()

    daemon = NameServerDaemon(host, port, unixsocket, nathost=nathost, natport=natport, storage=storage)
    nsUri = daemon.uriFor(daemon.nameserver)
    internalUri = daemon.uriFor(daemon.nameserver, nat=False)
    bcserver = None
    if unixsocket:
        hostip = "Unix domain socket"
    else:
        hostip = daemon.sock.getsockname()[0]
        if daemon.sock.family == socket.AF_INET6:       # ipv6 doesn't have broadcast. We should probably use multicast instead...
            log.info("Not starting NS broadcast server because NS is using IPv6")
            enableBroadcast = False
        elif hostip.startswith("127.") or hostip == "::1":
            log.info("Not starting NS broadcast server because NS is bound to localhost")
            enableBroadcast = False
        if enableBroadcast:
            # Make sure to pass the internal uri to the broadcast responder.
            # It is almost always useless to let it return the external uri,
            # because external systems won't be able to talk to this thing anyway.
            bcserver = BroadcastServer(internalUri, bchost, bcport, ipv6=daemon.sock.family == socket.AF_INET6)
            log.info("Broadcast server running on %s" % bcserver.locationStr)
            bcserver.runInThread()
    existing = daemon.nameserver.count()
    if existing > 1:   # don't count our own nameserver registration
        log.info("Persistent store contains %d existing registrations." % existing)
    log.info("NS running on %s (%s)" % (daemon.locationStr, hostip))
    if daemon.natLocationStr:
        log.info("internal URI = %s" % internalUri)
        log.info("external URI = %s" % nsUri)
    else:
        log.info("URI = %s" % nsUri)
    try:
        # Placed in a try block because this fails with pythonw.exe
        sys.stdout.flush()
    except:
        log.warning("Couldn't flush stdout! (Not a problem if running under pythonw.exe)")
    try:
        daemon.requestLoop(loopCondition=loop_condition)
    finally:
        daemon.close()
        if bcserver is not None:
            bcserver.close()
    log.info("NS shut down.")


def start_ns(cfg: NameServerConfiguration=None):
    """
    Utility fuction to quickly get a Nameserver daemon to be used in your own 
    event loops.
    
    Returns
    -------
    nameserverUri, nameserverDaemon, broadcastServer
        A tuple containing three pieces of information.
    """
    return start_ns(
        host=cfg.host, 
        port=cfg.ns_port, 
        enableBroadcast=cfg.broadcast, 
        bchost=cfg.bc_host, 
        bcport=cfg.bc_port,
        storage=cfg.storage
    )
