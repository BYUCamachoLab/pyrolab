# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
KCube
------

Submodule containing drivers for the ThorLabs Translational Stage controlled by
Brushed Motor Controller or DC Servo.
"""

from pyrolab.drivers.motion import Motion
from pyrolab.drivers.motion._kinesis.kdc101 import KDC101, HomingMixin

class Stage(Motion, KDC101, HomingMixin):
    """
    A PRM1Z8 precision motorized rotation stage controlled by a KCube DC Servo 
    motor.

    Parameters
    ----------
    serialno : int
        The serial number of the device to connect to.
    polling : int
        The polling rate in milliseconds.
    """
    def __init__(self, serialno, polling=200):
        super().__init__(serialno, polling)

    def get_position(self):
        pass

    def move(self, position):
        pass


