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

    activated = False

    def __init__(self,port):
        self.activated = True
        self.port = port

    def start(self):
        if(self.activated == False):
            raise Exception("Device is locked")

        self.board = pyfirmata.Arduino(self.port)

    def on(self,pin=13):
        if(self.activated == False):
            raise Exception("Device is locked")

        self.board.digital[pin].write(1)

    def off(self,pin=13):
        if(self.activated == False):
            raise Exception("Device is locked")

        self.board.digital[pin].write(0)
    
    def exit(self):
        if(self.activated == False):
            raise Exception("Device is locked")
            
        self.board.exit()