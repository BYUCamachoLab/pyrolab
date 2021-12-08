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

import logging
from typing import Dict, List, Optional

import Pyro5.nameserver

from pyrolab.utils.configure import Configuration
from pyrolab import PYROLAB_DATA_DIR


log = logging.getLogger(__name__)


NAMESERVER_DATA_DIR = PYROLAB_DATA_DIR / "nameserver" / "data"
NAMESERVER_DATA_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_FILE = NAMESERVER_DATA_DIR / "storage"


class NameServerConfiguration(Configuration):
    """
    The NameServer Configuration class. 
    
    Contains all applicable configuration parameters for running a nameserver.

    Parameters
    ----------
    host : str, optional
        The hostname of the nameserver. Defaults to "localhost".
    ns_port : int, optional
        The port of the nameserver. Defaults to 9090.
    broadcast : bool, optional
        Whether to launch a broadcast server. Defaults to False.
    ns_bchost : str, optional
        The hostname of the broadcast server. Defaults to None.
    ns_bcport : int, optional
        The port of the broadcast server. Defaults to 9091.
    ns_autoclean : float, optional
        The interval in seconds at which the nameserver will ping registered
        objects and clean up unresponsive ones. Default is 0.0 (off).
    storage_type : str, optional
        The type of storage to use for the nameserver. Defaults to "memory".
    storage_filename : str, optional
        The filename of the storage to use for the nameserver. Defaults to "".
        Can be specified if storage_type is "sql" or "dbm". If not specified,
        internal data directories will be used.

    Raises
    ------
    ValueError
        If the storage type is not one of "memory", "sql", or "dbm".
    """
    def __init__(self,
                 host: str="localhost",
                 ns_port: int=9090,
                 broadcast: bool=False,
                 ns_bchost: Optional[bool]=None,
                 ns_bcport: int=9091,
                 ns_autoclean: float=0.0,
                 storage_type: str="memory",
                 storage_filename: str="") -> None:
        super().__init__(
            host=host,
            ns_host=host,
            ns_port=ns_port,
            broadcast=broadcast,
            ns_bchost=ns_bchost,
            ns_bcport=ns_bcport,
            ns_autoclean=ns_autoclean,
        )
        if storage_type not in ("memory", "sql", "dbm"):
            raise ValueError("invalid storage type: " + storage_type)
        if storage_type != "memory" and not storage_filename:
            storage_filename = str(STORAGE_FILE.with_suffix(f".{storage_type}"))
        if storage_type == "sql":
            self.storage = f"sql:{storage_filename}"
        elif storage_type == "dbm":
            self.storage = f"dbm:{storage_filename}"
        elif storage_type == "memory":
            self.storage = storage_type
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")


# # Inheriting from the Nameserver
# class NameServer(Pyro5.nameserver.NameServer):
#     """
#     PyroLab specific NameServer with custom functionality including the ability
#     to reject duplicate registration names.
#     """
#     pass


def start_ns_loop(cfg: NameServerConfiguration=None) -> None:
    """
    Utility function that starts a new NameServer and enters its requestloop.

    Loop can be shut down using ``ctrl+c``.

    Parameters
    ----------
    cfg : NameserverConfiguration
        The configuration object for the nameserver.
    """
    Pyro5.nameserver.start_ns_loop(host=cfg.host, port=cfg.ns_port, 
        enableBroadcast=cfg.broadcast, bchost=cfg.ns_bchost, 
        bcport=cfg.ns_bcport, storage=cfg.storage)


def start_ns(cfg: NameServerConfiguration=None):
    """
    Utility fuction to quickly get a Nameserver daemon to be used in your own 
    event loops.
    
    Returns
    -------
    nameserverUri, nameserverDaemon, broadcastServer
        A tuple containing three pieces of information.
    """
    return Pyro5.nameserver.start_ns(host=cfg.host, 
        port=cfg.ns_port, enableBroadcast=cfg.broadcast, 
        bchost=cfg.bc_host, bcport=cfg.bc_port,
        storage=cfg.storage)
