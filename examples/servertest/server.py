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

import pyrolab.api
from pyrolab.drivers.sample import SampleService
pyrolab.api.config.reset(use_file=False)

daemon = pyrolab.api.Daemon()
ns = pyrolab.api.locate_ns(host="localhost")
uri = daemon.register(SampleService)
ns.register("test.SampleService", uri)

print("READY")
try:
    daemon.requestLoop()
finally:
    ns.remove("test.SampleService")
