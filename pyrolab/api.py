# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
API
===

A single module that centralizes the most frequently used objects from PyroLab.
"""

from Pyro5.client import Proxy
from Pyro5.core import locate_ns
from Pyro5.server import behavior, expose, oneway, serve
from pyrolab import USER_CONFIG_FILE
from pyrolab.configure import (
    PyroLabConfiguration, 
    NameServerConfiguration, 
    DaemonConfiguration, 
    ServiceConfiguration, 
    reset_config, 
    update_config,
)
from pyrolab.server import Daemon, LockableDaemon
from pyrolab.nameserver import start_ns, start_ns_loop
from pyrolab.service import Service


__all__ = [
    "locate_ns",
    "Proxy",
    "start_ns",
    "start_ns_loop",
    "Daemon",
    "LockableDaemon",
    "expose",
    "behavior",
    "oneway",
    "serve",
    "update_config",
    "reset_config",
    "Service",
    "PyroLabConfiguration",
    "NameServerConfiguration",
    "DaemonConfiguration",
    "ServiceConfiguration",
]

# If a user config file exists, load the first listed nameserver by default,
# so that locate_ns "just works." 
if USER_CONFIG_FILE.exists():
    cfg = PyroLabConfiguration.from_file(USER_CONFIG_FILE)
    nscfg = next(iter(cfg.nameservers.values()))
    nscfg.update_pyro_config()
