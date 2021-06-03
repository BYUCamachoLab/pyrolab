# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Instance Mode Client
--------------------

...
"""

from pyrolab.api import config, locate_ns, Proxy
config.reset()


print("\n-----PERCALL (different number possible every time)-----")
print("..Proxy 1..")
with Proxy("PYRONAME:instance.percall") as p:
    print(p.whoami())
    print(p.whoami())
print("..Proxy 2..")
with Proxy("PYRONAME:instance.percall") as p:
    print(p.whoami())
    print(p.whoami())

print("\n-----SESSION (same ID within session)-----")
print("..Proxy 1..")
with Proxy("PYRONAME:instance.session") as p:
    print(p.whoami())
    print(p.whoami())
print("..Proxy 2..")
with Proxy("PYRONAME:instance.session") as p:
    print(p.whoami())
    print(p.whoami())

print("\n-----SINGLE (same number always, even over proxies)-----")
print("..Proxy 1..")
with Proxy("PYRONAME:instance.single") as p:
    print(p.whoami())
    print(p.whoami())
print("..Proxy 2..")
with Proxy("PYRONAME:instance.single") as p:
    print(p.whoami())
    print(p.whoami())
