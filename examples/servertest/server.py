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

import pyrolab
pyrolab.config.reset(use_file=False)

from pyrolab.server import get_daemon
from pyrolab.drivers.sample import SampleService

daemon = get_daemon()
ns = pyrolab.api.locate_ns(host="localhost")
uri = daemon.register(SampleService)
ns.register("test.SampleService", uri)

print("READY")
daemon.requestLoop()
