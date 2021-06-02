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
uri1 = ns.lookup("test.SampleService")
uri2 = ns.lookup("test.SampleAutoconnectInstrument")

service1 = Proxy(uri1)
service2 = Proxy(uri2)

print("SERVICE 1")
print("---------")

resp = service1.echo("Hello, server!")
print(type(resp), resp)

resp = service1.delayed_echo("This response will be delayed by 2 seconds.", 2)
print(type(resp), resp)

print('\n')
print("SERVICE 2")
print("---------")

resp = service2.autoconnect()
print("Connected:", resp)

resp = service2.do_something()
print(type(resp), resp)
