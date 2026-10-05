# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Nameserver
==========

Wrapped nameserver functions that references PyroLab configuration settings.
"""

import logging
import socket
import sys
from pathlib import Path
from typing import Callable, Optional

from Pyro5.nameserver import BroadcastServer, NameServerDaemon
from Pyro5.nameserver import start_ns as _pyro_start_ns

from pyrolab.configure import NameServerConfiguration

log = logging.getLogger(__name__)


# # Inheriting from the Nameserver
# class NameServer(Pyro5.nameserver.NameServer):
#     """
#     PyroLab specific NameServer with custom functionality including the ability
#     to reject duplicate registration names.
#     """
#     pass


def _prepare_storage(storage: str) -> str:
    """Create the directory a "sql:..."/"dbm:..." storage file goes in."""
    kind, _, path = storage.partition(":")
    if kind in ("sql", "dbm") and path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return storage


def start_ns_loop(
    cfg: NameServerConfiguration,
    loop_condition: Callable = lambda: True,
    on_ready: Optional[Callable[[], None]] = None,
) -> None:
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
    on_ready : callable, optional
        Called with no arguments once the nameserver is bound and about to
        start serving requests.
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
    _prepare_storage(storage)
    cfg.update_pyro_config()

    daemon = NameServerDaemon(
        unixsocket, nathost=nathost, natport=natport, storage=storage
    )
    nsUri = daemon.uriFor(daemon.nameserver)
    internalUri = daemon.uriFor(daemon.nameserver, nat=False)
    bcserver = None
    if unixsocket:
        hostip = "Unix domain socket"
    else:
        hostip = daemon.sock.getsockname()[0]
        if (
            daemon.sock.family == socket.AF_INET6
        ):  # ipv6 doesn't have broadcast. We should probably use multicast instead...
            log.info("Not starting NS broadcast server because NS is using IPv6")
            enableBroadcast = False
        elif hostip.startswith("127.") or hostip == "::1":
            log.info(
                "Not starting NS broadcast server because NS is bound to localhost"
            )
            enableBroadcast = False
        if enableBroadcast:
            # Make sure to pass the internal uri to the broadcast responder.
            # It is almost always useless to let it return the external uri,
            # because external systems won't be able to talk to this thing anyway.
            bcserver = BroadcastServer(
                internalUri, bchost, bcport, ipv6=daemon.sock.family == socket.AF_INET6
            )
            log.info("Broadcast server running on %s" % bcserver.locationStr)
            bcserver.runInThread()
    existing = daemon.nameserver.count()
    if existing > 1:  # don't count our own nameserver registration
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
    except Exception:  # under pythonw, stdout is None
        log.warning(
            "Couldn't flush stdout! (Not a problem if running under pythonw.exe)"
        )
    if on_ready is not None:
        on_ready()
    try:
        daemon.requestLoop(loopCondition=loop_condition)
    finally:
        daemon.close()
        if bcserver is not None:
            bcserver.close()
    log.info("NS shut down.")


def start_ns(cfg: NameServerConfiguration):
    """
    Utility fuction to quickly get a Nameserver daemon to be used in your own
    event loops.

    Parameters
    ----------
    cfg : NameServerConfiguration
        The configuration object for the nameserver.

    Returns
    -------
    nameserverUri, nameserverDaemon, broadcastServer
        A tuple containing three pieces of information.
    """
    # Applies the host (resolving "public") to Pyro5.config.HOST, which the
    # NameServerDaemon falls back to when no host is passed.
    cfg.update_pyro_config()
    return _pyro_start_ns(
        port=cfg.ns_port,
        enableBroadcast=cfg.broadcast,
        bchost=cfg.ns_bchost,
        bcport=cfg.ns_bcport,
        storage=_prepare_storage(cfg.get_storage_location()),
    )
