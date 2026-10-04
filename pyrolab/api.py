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
# This is a convenience only: importing the API must never fail because the
# local configuration is invalid, has no nameservers, or names a "public"
# host that can't be resolved -- otherwise neither client scripts nor the
# CLI commands that would fix the configuration could even start.
if USER_CONFIG_FILE.exists():
    try:
        cfg = PyroLabConfiguration.from_file(USER_CONFIG_FILE)
        nscfg = next(iter(cfg.nameservers.values()), None)
        if nscfg is not None:
            nscfg.update_pyro_config()
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(
            "Not applying nameserver defaults from %s: %s", USER_CONFIG_FILE, e
        )
