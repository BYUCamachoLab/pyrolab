# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Using a lockable service
------------------------


"""

from pyrolab.api import locate_ns, Proxy

ns = locate_ns(host="localhost")
uri = ns.lookup("test.SampleAutoconnectInstrument")

# Note that proxies are not connected until the first method call is made.
# This means that the following two lines set up the proxies without actually
# connecting to the remote objects.
service = Proxy(uri)

resp = service.autoconnect()
print(type(resp), resp)

resp = service.do_something()
print(type(resp), resp)
