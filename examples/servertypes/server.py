# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Server Types Demonstration
--------------------------

Runs a class as either threaded or multiplexed, based on user input.

1. ``thread`` A single object is created but different proxies can call
   its functions simultaneously from different threads.
2. ``multiplex`` Only a single instance exists and it cannot be called from
   different threads; each call arriving is placed in a queue and executed
   sequentially.
"""

import threading
import time

from pyrolab.api import config, serve, locate_ns, expose, behavior, oneway
from pyrolab.drivers.sample import SampleService
config.reset(use_file=False)


@expose
@behavior(instance_mode="single")
class Server(SampleService):
    def __init__(self):
        self.callcount = 0

    def reset(self):
        self.callcount = 0

    def getcount(self):
        return self.callcount  # the number of completed calls

    def getconfig(self):
        return config._to_dict()

    def delay(self):
        threadname = threading.current_thread().getName()
        print("delay called in thread %s" % threadname)
        time.sleep(1)
        self.callcount += 1
        return threadname

    @oneway
    def onewaydelay(self):
        threadname = threading.current_thread().getName()
        print("onewaydelay called in thread %s" % threadname)
        time.sleep(1)
        self.callcount += 1


# main program

config.SERVERTYPE = "undefined"
servertype = input("Servertype threaded or multiplex (t/m)?")
if servertype == "t":
    config.SERVERTYPE = "thread"
else:
    config.SERVERTYPE = "multiplex"


if __name__ == "__main__":
    # please make sure a name server is running somewhere first.
    try:
        serve({
            Server: "example.servertypes"
        })
    finally:
        ns = locate_ns(host="localhost")
        ns.remove("example.servertypes")
