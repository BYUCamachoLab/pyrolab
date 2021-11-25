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
from pathlib import Path
from typing import Dict, List, Optional

import yaml
import Pyro5.nameserver

from pyrolab.utils.configure import Configuration
from pyrolab import PYROLAB_CONFIG_DIR, PYROLAB_DATA_DIR


log = logging.getLogger(__name__)


NAMESERVER_CONFIG_DIR = PYROLAB_CONFIG_DIR / "nameserver" / "config"
NAMESERVER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_CONFIG_FILE = NAMESERVER_CONFIG_DIR / "default.yaml"

NAMESERVER_DATA_DIR = PYROLAB_DATA_DIR / "nameserver" / "data"
NAMESERVER_DATA_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_FILE = NAMESERVER_DATA_DIR / "storage.sql"


class NameserverConfiguration(Configuration):
    """
    """
    def __init__(self,
                 host: str="localhost",
                 ns_port: int=9090,
                 broadcast: bool=False,
                 ns_bchost: Optional[bool]=None,
                 ns_bcport: int=9091,
                 ns_autoclean: float=0.0,
                 storage_type: str="sql",
                 storage_filename: str=f"{STORAGE_FILE}") -> None:
        super().__init__(
            host=host,
            ns_port=ns_port,
            broadcast=broadcast,
            ns_bchost=ns_bchost,
            ns_bcport=ns_bcport,
            ns_autoclean=ns_autoclean,
        )
        if storage_type == "sql":
            self.storage = f"sql:{storage_filename}"
        elif storage_type == "dbm":
            self.storage = f"dbm:{storage_filename}"
        elif storage_type == "memory":
            self.storage = storage_type
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")


def load_ns_configs(filename: str=None) -> Dict[str, NameserverConfiguration]:
    """
    Reads the nameserver configurations from a YAML file. 
    
    If no filename is provided, the default file from PyroLab's persistent
    data is used.

    Parameters
    ----------
    filename : str or Path, optional
        The path to the configuration file. If not provided, the default file
        from PyroLab's persistent data is used.

    Returns
    -------
    ns_configurations: Dict[str, NameserverConfiguration]
        A dictionary of configuration names to NameserverConfiguration objects.

    Examples
    --------
    Suppose we have the following configuration file:

    .. code-block:: yaml
        nameservers:
            - production:
                host: camacholab.ee.byu.edu
                ns_port: 9090
                broadcast: false
                ns_bchost: null
                ns_bcport: 9091
                ns_autoclean: 15.0
                storage_type: sql
            - development:
                host: localhost
                ns_port: 9090

    Note that, regardless of whether it is present in the file, the default
    configuration is always available. It has the following settings:

    .. code-block:: yaml
        nameservers:
            - default:
                host: localhost
                broadcast: false
                ns_port: 9090
                ns_bchost: localhost
                ns_bcport: 9091
                ns_autoclean: 0.0
                storage_type: sql
                storage_filename: <pyrolab default data directory>

    If a profile named "default" exists in the file, the base default is 
    overridden. Many places in PyroLab read the default configuration, so be
    careful and make sure you actually want to change the default.
    
    >>> from pyrolab.nameserver.configure import NameserverConfiguration
    >>> nsconfigs = NameserverConfiguration.load_configurations("nameservers.yaml")
    >>> list(nsconfigs.keys())
    ['default', 'production', 'development']
    """
    if filename is None:
        filename = DEFAULT_CONFIG_FILE
    else:
        filename = Path(filename)
    if not filename.exists():
        raise FileNotFoundError(f"Configuration file '{filename}' not found.")
    with open(filename, "r") as f:
        config = yaml.safe_load(f)
    ns_configurations = {"default": NameserverConfiguration()}
    if "nameservers" in config:
        for ns in config["nameservers"]:
            ns_name, ns_config = list(ns.items())[0]
            ns_configurations[ns_name] = NameserverConfiguration(**ns_config)
        return ns_configurations
    else:
        raise ValueError(f"Configuration file '{filename}' does not contain a 'nameservers' section.")


# # Inheriting from the Nameserver
# class NameServer(Pyro5.nameserver.NameServer):
#     """
#     PyroLab specific NameServer with custom functionality including the ability
#     to reject duplicate registration names.
#     """
#     pass


def start_ns_loop(cfg: NameserverConfiguration=None) -> None:
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


def start_ns(cfg: NameserverConfiguration=None):
    """
    Utility fuction to quickly get a Nameserver daemon to be used in your own 
    event loops.
    
    Returns
    -------
    nameserverUri, nameserverDaemon, broadcastServer
        A tuple containing three pieces of information.
    """
    enableBroadcast = False
    return Pyro5.nameserver.start_ns(host=cfg.host, 
        port=cfg.ns_port, enableBroadcast=cfg.broadcast, 
        bchost=cfg.bc_host, bcport=cfg.bc_port,
        storage=cfg.storage)
