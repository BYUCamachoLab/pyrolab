# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
-----------------------------------------------
Driver for the Arduino that is connected to a Thorlabs Microscope Lamp.
Author: David Hill (https://github.com/hillda3141)
Repo: https://github.com/BYUCamachoLab/pyrolab/blob/bpc303/pyrolab/drivers/motion
"""

import pyfirmata
import time
from Pyro5.api import expose
import pyrolab.api

@expose
class LAMP:

    def __init__(self,port):
        print("yeet2")
        self.port = port

    def start(self):
        self.board = pyfirmata.Arduino(self.port)

    def on(self,pin=13):
        self.board.digital[pin].write(1)

    def off(self,pin=13):
        self.board.digital[pin].write(0)
    
    def exit(self):
        self.board.exit()