# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
2-Way SSL Server
----------------

...
"""

from Pyro5.nameserver import start_ns_loop

import pyrolab
pyrolab.config.reset(use_file=False)

start_ns_loop(
    host=pyrolab.config.NS_HOST,
    port=pyrolab.config.NS_PORT,
    enableBroadcast=True,
)
