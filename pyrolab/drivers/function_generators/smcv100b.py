# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
R&S SMCV100B series VSG
=======================

.. admonition:: Dependencies
   :class: note

   | pyvisa
   | NI-VISA *or* pyvisa-py
"""

from typing import Optional

import pyvisa as visa

from pyrolab.drivers import VISAResourceExtensions
from pyrolab.drivers.function_generators import FunctionGenerator


class SMCV100B(FunctionGenerator):
    """
    Simple network controller class for R&S SMCV100B VSG.

    This class is used to control the R&S SMCV100B VSG. These are not local
    devices, nor native PyroLab objects. Therefore, network device
    autodetection is not supported.
    """

    @staticmethod
    def detect_devices():
        """
        Network device detection not supported.

        Because R&S VSGs are connected to using the IP address,
        this function does not detect them and instead always returns an empty
        list.
        """
        device_info = []
        return device_info

    def connect(self, address: str = "", timeout: float = 2e3) -> bool:
        """
        Connects to and initializes the VSG.

        Parameters
        ----------
        address : str
            The IP address of the instrument.
        timeout : int, optional
            The device response timeout in milliseconds (default 2 s).
            Pass ``None`` for infinite timeout.
        """
        rm = visa.ResourceManager()
        self.device = rm.open_resource(f"TCPIP0::{address}")
        self.device.timeout = timeout
        self.device.read_termination = "\n"
        self.write_termination = "\n"
        self.device.ext_clear_status()

        self.write("*RST;*CLS")
        self.write(":DISP:UPD ON")
        self.device.ext_error_checking()

        return True

    def close(self):
        self.device.close()

    @property
    def timeout(self):
        """
        Network timeout duration in milliseconds (errors out if no response
        received within timeout).
        """
        return self.device.timeout

    @timeout.setter
    def timeout(self, ms):
        self.device.timeout = ms

    def query(self, message: str = "", delay: Optional[float] = None):
        """
        A combination of :py:func:`write` and :py:func:`read`.

        Parameters
        ----------
        message : str
            The message to send.
        delay : float, optional
            Delay in seconds between write and read operations. If None,
            defaults to ``self.device.query_delay``.
        """
        return self.device.query(message, delay)

    def write(
        self,
        message: str,
        termination: Optional[str] = None,
        encoding: Optional[str] = None,
    ):
        """
        Writes a message to the VSG.

        Parameters
        ----------
        message : str
            The message to send.
        termination : str, optional
            Alternative character termination to use. If None, the value
            of write_termination is used. Defaults to None.
        encoding : str, optional
            Alternative encoding to use to turn str into bytes. If None,
            the value of encoding is used. Defaults to None.
        """
        self.device.write(message, termination, encoding)

    def write_block(self, message: str):
        """
        Writes a message to the VSG, waits for it to complete, and checks for errors.

        Parameters
        ----------
        message : str
            The message to send (not a query).

        Notes
        -----
        This function is blocking.
        """
        self.write(message)
        self.wait_for_device()
        self.device.ext_error_checking()

    def wait_for_device(self):
        """
        Waits for the device until last action is complete.

        Notes
        -----
        This function is blocking.
        """
        self.device.ext_wait_for_opc()

    def set_output(self, state: int):
        """
        Enables or disables the output of the VSG.

        Parameters
        ----------
        state : str
            Enables or disables the output of the VSG.
            1 = ON, 0 = OFF
        """
        self.write_block(f"OUTP:ALL:STAT {state}")

    def turn_on(self):
        """
        Turns on the output of the VSG.
        """
        self.set_output(1)

    def turn_off(self):
        """
        Turns off the output of the VSG.
        """
        self.set_output(0)

    def set_amp(self, amplitude: int):
        """
        Sets the amplitude of the VSG.

        Parameters
        ----------
        amplitude : int
            Sets the amplitude of the signal (in dBm)
        """
        self.write_block(f"SOUR:POW:LEV:AMPL {amplitude}")

    def set_amp_offset(self, offset: int):
        """
        Sets the amplitude level offset of the VSG.
        NOT a DC offset.

        Parameters
        ----------
        offset : int
            Sets the amplitude offset of the signal (in dB)
        """
        self.write_block(f"SOUR:POW:OFFS {offset}")

    def sweep_amp(self, start: int, stop: int, step: int, dwell: int = 1):
        """
        Sweeps the amplitude of the VSG between two values with a given step
        size and dwelling time.

        Parameters
        ----------
        start : int
            Sets the start amplitude of the sweep (in dBm)
        stop : int
            Sets the stop amplitude of the sweep (in dBm)
        step : int
            Sets the size of each step in the sweep (in dB)
        dwell : int
            Sets the dwelling time for each step of the sweep (in s). Default
            is 1 s.
        """
        self.write_block(f"SOUR:POW:MODE SWE")
        self.write_block(f"SOUR:POW:STAR {start}")
        self.write_block(f"SOUR:POW:STOP {stop}")
        self.write_block(f"SOUR:SWE:POW:STEP:LOG {step}")
        self.write_block(f"SOUR:SWE:POW:DWEL1 {dwell}")
        self.write_block(f"TRIG:PSW:SOUR SING")
        self.write_block(f"TRIG:PSW:IMM")

    def amp_running(self):
        """
        Checks if the amplitude sweep is running.

        Returns
        -------
        int
            1 = running, 0 = not running
        """
        return self.query("SOUR:SWE:POW:RUNN?")

    def amp_step_up(self, step: int):
        """
        Steps the amplitude of the VSG up by one step.

        Parameters
        ----------
        step : int
            Sets the size of the step (in dB)
        """
        self.write_block(f"SOUR:POW:STEP {step}")
        self.write_block(f"SOUR:POW:STEP:MODE USER")
        self.write_block(f"SOUR:POW:LEV:AMPL UP")

    def amp_step_down(self, step: int):
        """
        Steps the amplitude of the VSG down by one step.

        Parameters
        ----------
        step : int
            Sets the size of the step (in dB)
        """
        self.write_block(f"SOUR:POW:STEP {step}")
        self.write_block(f"SOUR:POW:STEP:MODE USER")
        self.write_block(f"SOUR:POW:LEV:AMPL DOWN")

    def set_freq(self, frequency: int):
        """
        Sets the frequency of the VSG.

        Parameters
        ----------
        frquency : int
            Sets the frequency of the signal (in Hz)
        """
        self.write_block(f"SOUR:FREQ:FIX {frequency}")

    def set_freq_offset(self, offset: int):
        """
        Sets the frequency offset of the VSG.

        Parameters
        ----------
        offset : int
            Sets the frequency offset of the signal (in Hz)
        """
        self.write_block(f"SOUR:FREQ:OFFS {offset}")

    def set_phase(self, phase: int):
        """
        Sets the phase of the VSG.

        Parameters
        ----------
        phase : int
            Sets the phase of the signal (in degrees)
        """
        self.write_block(f"SOUR:PHAS {phase}")

    def sweep_freq_lin(self, start: int, stop: int, step: int, dwell: int = 1):
        """
        Sweeps the frequency of the VSG linearly between two values with a
        given step size and dwelling time.

        Parameters
        ----------
        start : int
            Sets the start frequency of the sweep (in Hz)
        stop : int
            Sets the stop frequency of the sweep (in Hz)
        step : int
            Sets the size of each step in the sweep (in Hz)
        dwell : int
            Sets the dwelling time for each step of the sweep (in s). Default
            is 1 s.
        """
        self.write_block(f"SOUR:FREQ:MODE SWE")
        self.write_block(f"SOUR:FREQ:STAR {start}")
        self.write_block(f"SOUR:FREQ:STOP {stop}")
        self.write_block(f"SOUR:SWE:FREQ:STEP:LIN {step}")
        self.write_block(f"SOUR:SWE:FREQ:DWEL1 {dwell}")
        self.write_block(f"TRIG:FSW:SOUR SING")
        self.write_block(f"TRIG:FSW:IMM")

    def sweep_freq_log(self, start: int, stop: int, step: int, dwell: int = 1):
        """
        Sweeps the frequency of the VSG logarithmically between two values with
        a given step size and dwelling time.

        Parameters
        ----------
        start : int
            Sets the start frequency of the sweep (in Hz)
        stop : int
            Sets the stop frequency of the sweep (in Hz)
        step : int
            Sets the size of each step in the sweep (as a percentage of
            previous frequency)
        dwell : int
            Sets the dwelling time for each step of the sweep (in s). Default
            is 1 s.
        """
        self.write_block(f"SOUR:FREQ:MODE SWE")
        self.write_block(f"SOUR:FREQ:STAR {start}")
        self.write_block(f"SOUR:FREQ:STOP {stop}")
        self.write_block(f"SOUR:SWE:FREQ:SPAC LOG")
        self.write_block(f"SOUR:SWE:FREQ:STEP:LOG {step}")
        self.write_block(f"SOUR:SWE:FREQ:DWEL1 {dwell}")
        self.write_block(f"TRIG:FSW:SOUR SING")
        self.write_block(f"TRIG:FSW:IMM")

    def freq_running(self):
        """
        Checks if the frequency sweep is running.

        Returns
        -------
        int
            1 = running, 0 = not running
        """
        return self.query("SOUR:SWE:FREQ:RUNN?")

    def freq_step_up(self, step: float = 1e6):
        """
        Steps the frequency of the VSG up by one step.

        Parameters
        ----------
        step : int
            Sets the size of the step (in Hz)
        """
        self.write_block(f"SOUR:FREQ:STEP {step}")
        self.write_block(f"SOUR:FREQ:STEP:MODE USER")
        self.write_block(f"SOUR:FREQ:FIX UP")

    def freq_step_down(self, step: float = 1e6):
        """
        Steps the frequency of the VSG down by one step.

        Parameters
        ----------
        step : int
            Sets the size of the step (in Hz)
        """
        self.write_block(f"SOUR:FREQ:STEP {step}")
        self.write_block(f"SOUR:FREQ:STEP:MODE USER")
        self.write_block(f"SOUR:FREQ:FIX DOWN")

    def reset_sweeps(self):
        """
        Resets all active sweeps to the starting point.
        """
        self.write_block(f"SOUR:SWE:RES:ALL")

    def shut_down(self):
        """
        Shuts down the VSG.
        """
        self.write(f"SYST:SHUT")
