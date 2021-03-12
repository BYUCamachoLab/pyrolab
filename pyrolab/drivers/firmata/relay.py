# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
-----------------------------------------------
Driver for the Arduino that is connected to a Thorlabs Microscope Lamp.
Author: David Hill (https://github.com/hillda3141)
Repo: https://github.com/BYUCamachoLab/pyrolab/pyrolab/drivers/firmata
"""

import pyfirmata
from Pyro5.errors import PyroError
from Pyro5.api import expose
import pyrolab.api

@expose
class ArduinoRelay:

    def __init__(self,port):
        """"
        ArduinoRelay constructor.

        Parameters
        ----------
        port : string
            Port name that the arduino is connected to. Ex: "COM4"
        """
        self._activated = True
        self.port = port
        self.board = pyfirmata.Arduino(self.port)             

    def on(self,pin=13):
        """"
        Tell the arduino to turn a pin HIGH.

        Parameters
        ----------
        pin : int
            Integer that represents the digital out pin number on an arduino. Ex: 13
        """

        self.board.digital[pin].write(1)

    def off(self,pin=13):
        """"
        Tell the arduino to turn a pin LOW.

        Parameters
        ----------
        pin : int
            Integer that represents the digital out pin number on an arduino. Ex: 13
        """

        self.board.digital[pin].write(0)

    def close(self):
        """"
        Close the connection with the arduino.
        """
        
        self.off()
        self.board.exit()
    
    def __del__(self):
        """"
        Function called when Proxy connection is lost.
        """
        
        self.close()
