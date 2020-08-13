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

import pyrolab.api
from pyrolab.client import get_proxy

ns = pyrolab.api.locate_ns(host="localhost")
uri = ns.lookup("test.SampleService")

service = get_proxy(uri)

resp = service.echo("Hello, server!")
print(type(resp), resp)

resp = service.multiply(4, 5, 100)
print(type(resp), resp)
