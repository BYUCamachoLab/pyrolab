# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

import os

import numpy as np
import pytest

from pyrolab.drivers.motion.nanomax300 import NanoMax300


if sys.version_info < (3, 8, 0):
    os.environ['PATH'] = "C:\\Program Files\\Thorlabs\\Kinesis" + ";" + os.environ['PATH']
else:
    os.add_dll_directory("C:\\Program Files\\Thorlabs\\Kinesis")


def test_nanomax():
    nm = NanoMax300("71874833", closed_loop=True)
    # p = piezo.get_pos(1)
    # print(p)
    # piezo.home()
    # #bp.move_to(20000,20000,20000)
    # piezo.set_home(5000,10000,5000)
    # piezo.home()
    # x,y,z = piezo.get_all()
    # print("Point: (", x, ",", y, ",", z, ")")
    # for i in range(10):
    #     piezo.jog_all(i*10,i*10,i*10)
    #     x,y,z = piezo.get_all()
    #     print("Point: (", x, ",", y, ",", z, ")")
    #     piezo.fine_tune()
    #     x,y,z = piezo.get_all()
    #     print("F-Point: (", x, ",", y, ",", z, ")")
    # piezo.move_to(5000,5000,5000)
    # x,y,z = piezo.get_all()
    # p = piezo.get_pos(1)
    # print(p)
    # print("Point: (", x, ",", y, ",", z, ")")
    # disconnected = piezo.end()
    # if disconnected == 0:
    #     print("Could not disconnect")
