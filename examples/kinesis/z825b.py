import time

from pyrolab.api import NameServerConfiguration, Proxy, locate_ns
import numpy as np


nscfg = NameServerConfiguration(host="camacholab.ee.byu.edu")
nscfg.update_pyro_config()

with locate_ns() as ns:
    motor = Proxy(ns.lookup("asgard.hulk"))

motor.autoconnect()
print(motor.get_position())
motor.close()
