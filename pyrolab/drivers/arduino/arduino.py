# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Arduino Parent Driver
--------------------------------

Driver for Arduino that is running firmata code

Contributors
 * David Hill (https://github.com/hillda3141)

Original repo: https://github.com/BYUCamachoLab/pyrolab
Arduino should be running example code found under standard Arduino examples:
Examples/Firmata/StandardFirmata or similar code if the device memory is not large enough.
Code also stored locally in pyrolab/arduino/arduino_code/StandardFirmata.ino

.. admonition:: Dependencies
   :class: note

   pyfirmata
"""

from pyfirmata import Arduino, ArduinoMega, ArduinoDue, ArduinoNano, util

from Pyro5.api import expose
from pyrolab.arduino.errors import UnknownBoardException
from pyrolab.arduino import Arduino

@expose
class StandardArduinoDriver(Arduino):

    def connect(self, port: str, board: str="uno") -> None:
        """"
        Initialize a connection with the arduino.

        Parameters
        ----------
        port : str
            Computer serial port to which the arduino is connected
        board : str
            | The type of the arduino that is being used
            | uno: Arduino Uno (https://store.arduino.cc/products/arduino-uno-rev3)
            | mega: Arduino Mega (https://store.arduino.cc/products/arduino-mega-2560-rev3)
            | due: Arduino Due (https://store.arduino.cc/products/arduino-due)
            | nano: Arduino Nano (https://store.arduino.cc/products/arduino-nano)
        """
        self.port = port

        if board == "uno":
            self.board = Arduino(self.port)
        else if board == "mega":
            self.board = ArduinoMega(self.port)
        else if board == "due":
            self.board = ArduinoDue(self.port)
        else if board == "nano":
            self.board = ArduinoNano(self.port)
        else:
            raise UnknownBoardException("Unknown board " + board)

    def digital_write(self, pin: int, value: int) -> None:
        """"
        Tell the arduino to turn a pin digitally to the inputed value.

        Parameters
        ----------
        pin : int
            Integer that represents the digital out pin number on an arduino
        value : int
            | The value of the digital pin to be set
            | 0: LOW
            | 1: HIGH
        """
        command_string = "d:" + str(pin) + ":o"
        pin = self.board.get_pin(command_string)
        pin.write(value)
    
    def pwm_write(self, pin: int, value: float) -> None:
        """"
        Tell the arduino to produce a pwm signal on a pin.

        Parameters
        ----------
        pin : int
            Integer that represents the digital out pin number on an arduino
        value : float
            The duty cycle of the pwm to be set (0 - 1.0)
        """

        command_string = "d:" + str(pin) + ":p"
        pin = self.board.get_pin(command_string)
        pin.write(value)
    
    def servo_write(self, pin: int, value: int) -> None:
        """"
        Tell the arduino to configure a pin to drive a servo to
        the inputed angle.

        Parameters
        ----------
        pin : int
            Integer that represents the digital out pin number on an arduino
        value : int
            The angle in degrees to move the servo to
        """

        self.board.servo_config(pin)
        self.board.digital[pin].write(value)
    
    def digital_read(self, pin: int) -> int:
        """"
        Tell the arduino to read a value from a digital pin.

        Parameters
        ----------
        pin : int
            Integer that represents the digital in pin number on an arduino
        
        Returns
        -------
        int
            The value read by the digital pin, 0 (LOW) or 1 (HIGH)
        """

        command_string = "d:" + str(pin) + ":i"
        pin = self.board.get_pin(command_string)
        return pin.read()
    
    def analog_read(self, pin: int) -> float:
        """"
        Tell the arduino to read a value from an analog pin.

        Parameters
        ----------
        pin : int
            Integer that represents the analog in pin number on an arduino
        
        Returns
        -------
        float
            The value read by the analog pin (0 - 1.0)
        """

        command_string = "a:" + str(pin) + ":i"
        pin = self.board.get_pin(command_string)
        return pin.read()

    def close(self) -> None:
        """"
        Close the connection with the arduino.
        """
        
        self.board.exit()
