# -*- coding: utf-8 -*-
#
# Copyright © Sequoia Ploeg
# Licensed under the terms of the MIT License
# (see pyrolab/__init__.py for details)

"""
API
---

A single module that centralizes the most frequently used objects from PyroLab.
"""

from pyrolab.configure import global_config as config
from Pyro5.core import locate_ns
from pyrolab.client import Proxy, CertCheckingProxy
from pyrolab.server import Daemon, CertValidatingDaemon, expose
from pyrolab.nameserver import start_ns_loop



__all__ = [
    "config",
    "locate_ns", 
    "Proxy",
    "CertCheckingProxy",
    "Daemon",
    "CertValidatingDaemon", 
    "expose",
    "start_ns_loop",
]
