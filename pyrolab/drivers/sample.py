# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Sample Services
===============

This module implements some simple, sample services for testing whether a server
is working properly.
"""

import logging
import time
from typing import Union

from pyrolab.api import behavior, expose
from pyrolab.drivers import Instrument
from pyrolab.service import Service

log = logging.getLogger(__name__)
log.debug("Sample module loaded")


Number = Union[int, float]


@expose
class SampleService(Service):
    """
    A sample service with a few stubbed functions.
    """
    def __init__(self):
        log.info("SampleService created")
        pass

    def close(self):
        log.info("SampleService closed")
        pass

    def echo(self, message: str) -> str:
        """
        Echoes back as the response the exact message as received with
        "SERVER RECEIVED: " prepended to the message.

        Parameters
        ----------
        message : str
            The message to be echoed by the server.
        
        Returns
        -------
        resp : str
            The message to be echoed, prepended with "SERVER RECEIVED: ".
        """
        return "SERVER RECEIVED: " + message

    def delayed_echo(self, message: str, seconds: int) -> str:
        """
        Echoes back as the response the exact message as received with
        "SERVER RECEIVED: " prepended to the message after delaying by the
        specified number of seconds. 

        This function demonstrates that the connection does not die out even
        for long running requests.

        Parameters
        ----------
        message : str
            The message to be echoed by the server.
        seconds : int
            The number of seconds the server should wait before responding.
        
        Returns
        -------
        resp : str
            The message to be echoed, prepended with "SERVER RECEIVED: ".
        """
        time.sleep(seconds)
        return "SERVER RECEIVED: " + message

    def whoami(self):
        """
        Returns the object id of the instance that handled the request.

        Returns
        -------
        resp : str
            The object id of the handling instance.
        """
        return "OBJECT ID: " + str(id(self))

    def add(self, *a: Number) -> Number:
        """
        Adds an unconstrained number of arguments together.

        Parameters
        ----------
        a : Number
            Any number of arguments to be added together.

        Returns
        -------
        resp : Number
            The result of the addition.
        """
        return sum(a)

    def subtract(self, a: Number, b: Number) -> Number:
        """
        Subtracts the second parameter from the first.

        Parameters
        ----------
        a : Number
            The number to be subtracted from.
        b : Number
            The number to be subtracted.

        Returns
        -------
        resp : Number
            The result of the subtraction.
        """
        return a - b

    def multiply(self, *vals: Number) -> Number:
        """
        Multiplies an unconstrained number of arguments together.

        Parameters
        ----------
        vals : Number
            Any number of arguments to be multiplied together.

        Returns
        -------
        resp : Number
            The result of the multiplication.
        """
        final = 1
        for val in vals:
            final = final * val
        return final

    def divide(self, num: Number, den: Number) -> Number:
        """
        Divides the first argument by the second.

        Parameters
        ----------
        num : Number
            The numerator.
        den : Number
            The denominator.

        Returns
        -------
        resp : Number
            The result of the division.
        """
        return num / den


@behavior(instance_mode="single")
@expose
class SampleAutoconnectInstrument(Instrument):
    """
    A service that mocks a hardware instrument with connection parameters.

    This service will only be accessible if your configuration file lists the
    autoconnect parameters correctly.
    """
    def __init__(self) -> None:
        self.connected = False

    def close(self):
        """
        Close the hosting computer's connection with the hardware instrument.
        """
        self.connected = False

    def connect(self, address="localhost", port=9090) -> bool:
        """
        Connect to the hardware instrument. Default parameters are invalid.

        Parameters
        ----------
        address : str
            The address of the hardware instrument. Must be "0.0.0.0" for 
            successful connection.
        port : int
            The port of the hardware instrument. Must be any integer besides
            9090 for successful connection.

        Returns
        -------
        connected : bool
            Whether or not the connection was successful.
        """
        if address != "0.0.0.0":
            raise Exception("This test method requires address to be '0.0.0.0'.")
        if port == 9090:
            raise Exception("This test method requires the port to not be the default of 9090.")
        self.connected = True
        return True

    def do_something(self):
        """
        A method that does nothing and passes silently.
        
        Raises
        ------
        Exception
            If no successful connection has been made.
        """
        if not self.connected:
            raise Exception("This object cannot do work until connection is made.")
        return True

    def whoami(self):
        """
        Returns the object id of the instance that handled the request.

        Returns
        -------
        resp : str
            The object id of the handling instance.
        """
        return "OBJECT ID: " + str(id(self))
