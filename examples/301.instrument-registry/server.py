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

import multiprocessing
import signal

from pyrolab.api import locate_ns
from pyrolab.server import LockableDaemon, AutoconnectLockableDaemon, srv_profile, ServerConfiguration
from pyrolab.server.registry import registry

cfg = ServerConfiguration(servertype="multiplex")
srv_profile.use(cfg)

def worker(info, ns):
    name = multiprocessing.current_process().name
    print(f"Starting '{name}'")

    cls = info.get_class()
    # SS = behavior(SS, instance_mode="single")
    cls._pyroInstancing = ("single", None)

    if info.connect_params:
        daemon = AutoconnectLockableDaemon()
        uri = daemon.register(cls, connect_params=info.connect_params)
    else:
        daemon = LockableDaemon()
        uri = daemon.register(cls)

    ns.register(info.registered_name, uri, metadata=info.metadata)

    daemon.requestLoop()
    print(f"Exiting '{name}'")

service_names = []
jobs = []
ns = locate_ns(host="localhost")

def signal_handler(sig, frame):
    print('Terminating daemons...')
    for job in jobs:
        job.terminate()
        job.join()

# For Windows machines, all process creation must be guarded in
# __name__ == "__main__"
if __name__ == "__main__":
    for item in registry:
        service_names.append(item.registered_name)
        print(f"Registering {item.registered_name}...")

        p = multiprocessing.Process(name=f'daemon_{item.registered_name}', target=worker, args=(item, ns,))
        jobs.append(p)
        p.start()

    print("READY")

    try:
        signal.signal(signal.SIGINT, signal_handler)
        print('Press Ctrl+C to kill...')
    finally:
        pass
