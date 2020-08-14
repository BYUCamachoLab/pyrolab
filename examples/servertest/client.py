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
pyrolab.api.config.reset(use_file=False)

ns = pyrolab.api.locate_ns(host="localhost")
uri = ns.lookup("test.SampleService")

service = pyrolab.api.Proxy(uri)

resp = service.echo("Hello, server!")
print(type(resp), resp)

resp = service.delayed_echo("This response will be delayed by 2 seconds.", 2)
print(type(resp), resp)

resp = service.multiply(4, 5, 100)
print(type(resp), resp)
