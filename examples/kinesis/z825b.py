# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Kinesis KCube Driver Example
============================

This example demonstrates the use of the Thorlabs KCube DC Servo controlling a 
Z825B translational stage using PyroLab. 
"""

from pyrolab.api import NameServerConfiguration, Proxy, locate_ns


nscfg = NameServerConfiguration(host="yourdomain.com")
nscfg.update_pyro_config()

# Be considerate; don't stay connected to the nameserver too long.
with locate_ns() as ns:
    motor = Proxy(ns.lookup("Z825B_PyroName"))

motor.autoconnect()
print(motor.get_position())
motor.close()
