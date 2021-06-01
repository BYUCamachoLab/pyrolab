# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Autocleaning Nameserver
-----------------------

This namserver configuration is set to autoclean every 2.0 seconds.
"""

from pyrolab.api import start_ns_loop, ns_profile, NameserverConfiguration

cfg = NameserverConfiguration(ns_autoclean=1.0)
ns_profile.use(cfg)

start_ns_loop()
