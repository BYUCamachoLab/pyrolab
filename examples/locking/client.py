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
uri = ns.lookup("test.SampleService")

# Note that proxies are not connected until the first method call is made.
# This means that the following two lines set up the proxies without actually
# connecting to the remote objects.
service1 = Proxy(uri)
service2 = Proxy(uri)

resp = service1.echo("Hello, server!")
print(type(resp), resp)

resp = service1.delayed_echo("This response will be delayed by 2 seconds.", 2)
print(type(resp), resp)

resp = service1.multiply(4, 5, 100)
print(type(resp), resp)

# If two Proxies connect before an object is locked, both have access.
# Locking an object only blocks *subsequent* connection requests.

service1.lock()
# Since the next line is the first method call, the Proxy will try
# to connect and fail.
service2.add(2, 3) 
