# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
API
---

A single module that centralizes the most frequently used objects from PyroLab.
"""

from Pyro5.core import locate_ns
from Pyro5.client import Proxy

from pyrolab.nameserver import (
    NameServerConfiguration, 
    start_ns, 
    start_ns_loop
)
from pyrolab.daemon import (
    DaemonConfiguration, 
    Daemon, 
    LockableDaemon,
    expose,
    behavior,
    oneway,
    # serve,
    change_behavior
)


__all__ = [
    "locate_ns",
    "Proxy",
    "NameServerConfiguration",
    "start_ns",
    "start_ns_loop",
    "DaemonConfiguration",
    "Daemon",
    "LockableDaemon",
    "expose",
    "behavior",
    "change_behavior",
    "oneway",
    # "serve",
]
