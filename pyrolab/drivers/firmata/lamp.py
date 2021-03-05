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

Functions
---------
    __init__(self,port)
    start(self)
    on(self,pin=13)
    off(self,pin=13)
    close(self)
    __del__(self)
"""

import pyfirmata
import time
from Pyro5.errors import PyroError
from Pyro5.api import expose
import pyrolab.api

@expose
class LAMP:

    def __init__(self,port):
        """"
        LAMP constructor.

        Parameters
        ----------
        port : string
            Port name that the arduino is connected to. Ex: "COM4"
        """
        self._activated = True
        self.port = port

    def start(self):
        """"
        Initialize a connection with the arduino.

        Parameters
        ----------
        self.port : string
            Port name that is initialized in __init__(). Ex: "COM4"
        
        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")

        self.board = pyfirmata.Arduino(self.port)        

    def on(self,pin=13):
        """"
        Tell the arduino to turn a pin HIGH.

        Parameters
        ----------
        self.board : pyfirmata.Arduino
            Oject that represents an arduino initialized in start(). Ex: pyfirmata.Arduino("COM4")
        pin : int
            Integer that represents the digital out pin number on an arduino. Ex: 13
        
        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")

        self.board.digital[pin].write(1)

    def off(self,pin=13):
        """"
        Tell the arduino to turn a pin LOW.

        Parameters
        ----------
        self.board : pyfirmata.Arduino
            Oject that represents an arduino initialized in start(). Ex: pyfirmata.Arduino("COM4")
        pin : int
            Integer that represents the digital out pin number on an arduino. Ex: 13
        
        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")

        self.board.digital[pin].write(0)

    def close(self):
        """"
        Close the connection with the arduino.

        Parameters
        ----------
        self.board : pyfirmata.Arduino
            Oject that represents an arduino initialized in start(). Ex: pyfirmata.Arduino("COM4")
        pin : int
            Integer that represents the digital out pin number on an arduino. Ex: 13
        
        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")

        self.board.exit()
    
    def __del__(self):
        """"
        Function called when Proxy connection is lost.
        """
        self.close()