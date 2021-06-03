# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Instance Mode Server
--------------------

Registers the same class, SampleService, with the nameserver in three 
different modes:

1. ``single`` A single instance is created and all calls, across proxies, 
   access the same object.
2. ``session`` An instance is created per incoming Proxy connection. Until
   the connection is closed, the same instance is used. Simultaneous Proxies
   get their own instance.
3. ``percall`` An instance is created for each call, even if it's from the 
   same Proxy connection.
"""

from pyrolab.api import config, behavior, serve, locate_ns
from pyrolab.drivers.sample import SampleService
config.reset()


@behavior(instance_mode="single")
class SingleInstance(SampleService):
    pass


@behavior(instance_mode="session")
class SessionInstance(SampleService):
    pass


@behavior(instance_mode="percall")
class PercallInstance(SampleService):
    pass


if __name__ == "__main__":
    # please make sure a name server is running somewhere first.
    try:
        serve({
            SingleInstance: "instance.single",
            SessionInstance: "instance.session",
            PercallInstance: "instance.percall"
        }, verbose=True)
    finally:
        ns = locate_ns(host="localhost")
        ns.remove("instance.single")
        ns.remove("instance.session")
        ns.remove("instance.percall")
