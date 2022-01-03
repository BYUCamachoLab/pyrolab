# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Lockable service
----------------

This daemon supports registration of one object only, typically to be used
with Lockable services.

A feature of the LockableDaemon is that when the client connection is closed,
the lock on the Service is also released. (This is in case a client 
accidentally forgets to release the lock before closing the connection. Since 
all new connections are blocked until the lock is released, the client would 
not be able to reconnect to release the lock if not for this feature.)
"""

from pyrolab.api import locate_ns
from pyrolab.drivers.sample import SampleService
from pyrolab.server.locker import create_lockable
from pyrolab.server import LockableDaemon, srv_profile, DaemonConfiguration

cfg = DaemonConfiguration(servertype="multiplex")
srv_profile.use(cfg)

daemon = LockableDaemon()
ns = locate_ns(host="localhost")
SS = create_lockable(SampleService)
# SS = behavior(SS, instance_mode="single")
SS._pyroInstancing = ("single", None)
uri = daemon.register(SS)
ns.register("test.SampleService", uri, metadata={"You can put lists of strings here!"})

print("READY")
try:
    daemon.requestLoop()
finally:
    ns.remove("test.SampleService")
