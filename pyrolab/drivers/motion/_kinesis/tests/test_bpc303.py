# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

import os

import numpy as np
import pytest

from pyrolab.drivers.motion._kinesis import bpc303 as bp


if sys.version_info < (3, 8, 0):
    os.environ['PATH'] = "C:\\Program Files\\Thorlabs\\Kinesis" + ";" + os.environ['PATH']
else:
    os.add_dll_directory("C:\\Program Files\\Thorlabs\\Kinesis")


def test_bpc303():
    piezo = bp.BPC303("71874833", closed_loop=True)
    print("Connected!")
    # print("Zeroing (with blocking)")
    # piezo.zero()
    # print("Complete.")
    # for i in range(3):
    #     piezo.identify(i+1)
    #     time.sleep(1)
    if piezo.check_connection():
        print("Still connected!")
    print("Control mode (2?):", piezo.get_position_control_mode(1))
    print("Control mode (2?):", piezo.get_position_control_mode(2))
    print("Control mode (2?):", piezo.get_position_control_mode(3))
    print("Printing position:")
    for i in range(10):
        print("x:", piezo.voltage(1))
        print("y:", piezo.voltage(2))
        print("z:", piezo.voltage(3))
        time.sleep(1)
    piezo.close()
