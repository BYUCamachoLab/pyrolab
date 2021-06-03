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

from pyrolab.api import Daemon, locate_ns
from pyrolab.drivers.sample import SampleService

daemon = Daemon()
ns = locate_ns(host="localhost")
uri = daemon.register(SampleService)
ns.register("test.SampleService", uri)

print("READY")
try:
    daemon.requestLoop()
finally:
    ns.remove("test.SampleService")
