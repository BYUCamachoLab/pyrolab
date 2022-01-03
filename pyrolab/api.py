# -*- coding: utf-8 -*-
#
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

from pyrolab.configure import GlobalConfiguration, reset_config, update_config
from pyrolab.server import (  # serve,
    Daemon,
    LockableDaemon,
    behavior,
    change_behavior,
    expose,
    oneway,
)
from pyrolab.nameserver import start_ns, start_ns_loop
from pyrolab.service import Service

config = GlobalConfiguration.instance()


__all__ = [
    "locate_ns",
    "Proxy",
    "start_ns",
    "start_ns_loop",
    "Daemon",
    "LockableDaemon",
    "expose",
    "behavior",
    "change_behavior",
    "oneway",
    # "serve",
    "config",
    "update_config",
    "reset_config",
    "Service",
]
