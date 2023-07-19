# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Arduino Driver
==============

Driver for Arduino that is running firmata code.

Arduino should be running example code found under standard `Arduino Firmata
examples`_, or similar code if the device memory is not large enough. See:

* SimpleDigitalFirmata
* StandardFirmata

.. _Arduino Firmata examples: https://github.com/firmata/arduino

Code also available in the PyroLab repository under ``/extras/arduino``.

.. admonition:: Dependencies
   :class: note

   pyfirmata
"""

import logging
import subprocess
import serial
from psutil import process_iter
from signal import SIGTERM

from pyfirmata import (
    ANALOG,
    INPUT,
    OUTPUT,
    PWM,
    SERVO,
    Arduino,
    ArduinoDue,
    ArduinoMega,
    ArduinoNano,
    util,
)

from pyrolab.drivers.arduino import Arduino as PyroArduino
from pyrolab.api import expose


log = logging.getLogger(__name__)


@expose
class BaseArduinoDriver(PyroArduino):
    """
    A base class providing pin read/write access for common Arduino boards.
    """

    def connect(self, port: str, board: str = "uno") -> None:
        """
        Initialize a connection with the arduino. If the arduino is already connected to another process
        this will also kill that program.

        Parameters
        ----------
        port : str
            Computer serial port to which the arduino is connected
        board : str, optional
            | The type of the arduino that is being used:
            | ``uno``: `Arduino Uno <https://store.arduino.cc/products/arduino-uno-rev3>`_
            | ``mega``: `Arduino Mega <https://store.arduino.cc/products/arduino-mega-2560-rev3>`_
            | ``due``: `Arduino Due <https://store.arduino.cc/products/arduino-due>`_
            | ``nano``: `Arduino Nano <https://store.arduino.cc/products/arduino-nano>`_

        Raises
        ------
        ValueError
            If the board type is not supported.
        """
        if hasattr(self, "board"):
            log.debug("Already connected")
            return True

        self.port = port

        if board == "uno":
            self.board = Arduino(self.port)
        elif board == "mega":
            self.board = ArduinoMega(self.port)
        elif board == "due":
            self.board = ArduinoDue(self.port)
        elif board == "nano":
            self.board = ArduinoNano(self.port)
        else:
            raise ValueError(f"Unknown board '{board}'")

        try:
            self.it = util.Iterator(self.board)
            self.it.start()
        except Exception as e:
            self.close()
            raise e

    def digital_write(self, pin: int, value: int) -> None:
        """
        Tell the arduino to turn a pin digitally to the inputted value.

        Parameters
        ----------
        pin : int
            Integer that represents the digital out pin number on an arduino
        value : int
            | The value of the digital pin to be set
            | 0: LOW
            | 1: HIGH
        """
        self.board.digital[pin].mode = OUTPUT
        pin = self.board.digital[pin].write(value)

    def pwm_write(self, pin: int, value: float) -> None:
        """
        Tell the arduino to produce a pwm signal on a pin.

        Parameters
        ----------
        pin : int
            Integer that represents the digital out pin number on an arduino
        value : float
            The duty cycle of the pwm to be set (0 - 1.0)
        """
        self.board.digital[pin].mode = PWM
        self.board.digital[pin].write(value)

    def servo_write(self, pin: int, value: int) -> None:
        """
        Tell the arduino to configure a pin to drive a servo to
        the inputed angle.

        Parameters
        ----------
        pin : int
            Integer that represents the digital out pin number on an arduino
        value : int
            The angle in degrees to move the servo to
        """
        self.board.digital[pin].mode = SERVO
        self.board.digital[pin].write(value)

    def digital_read(self, pin: int) -> int:
        """
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
        self.board.digital[pin].mode = INPUT
        return self.board.digital[pin].read()

    def analog_read(self, pin: int) -> float:
        """
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
        # self.board.iterate()
        self.board.analog[pin].mode = INPUT
        self.board.analog[pin].enable_reporting()
        while True:
            value = self.board.analog[pin].read()
            if value is not None:
                break
        return value

    def close(self) -> None:
        """
        Close the connection with the arduino.
        """
        self.board.exit()
        del self.board
