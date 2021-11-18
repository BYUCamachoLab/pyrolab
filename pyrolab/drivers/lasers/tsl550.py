# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Santec Tunable Semiconductor Laser 550 (TSL550)
-----------------------------------------------

Driver for the Santec TSL-550 Tunable Laser.

Contributors
 * Wesley Cassidy (https://github.com/wecassidy)
 * Sequoia Ploeg (https://github.com/sequoiap)

Original repo: https://github.com/wecassidy/TSL550

.. note::

   The Santec TSL-550 drivers, which among other things, makes the USB 
   connection appear as a serial port, must be installed.

.. admonition:: Dependencies
   :class: note

   pyserial
"""

import sys
import time
import struct
import logging
from typing import Any, Dict, List

import serial
from serial.tools import list_ports

from pyrolab.api import expose, behavior
from pyrolab.drivers.lasers import Laser


log = logging.getLogger("pyrolab.drivers.lasers.tsl550")
# logger = logging.getLogger(__name__)


@behavior(instance_mode="single")
@expose
class TSL550(Laser):
    """
    Driver for the Santec TSL-550 laser.

    The laser must already be physically turned on and connected to a USB port
    of some host computer, whether that be a local machine or one hosted by 
    a PyroLab server. Methods such as :py:func:`on` and :py:func:`off` will 
    simply turn the laser diode on and off, not the laser itself.

    .. warning::

       An unidentifiable bug results in the return value of some functions 
       being the setting of the laser BEFORE the update (instead of the 
       commanded setting). To verify some value has been set to the commanded 
       value, simply call its respective function a second time without any 
       arguments.

    Attributes
    ----------
    MINIMUM_WAVELENGTH : float
        The minimum wavelength of the laser in nanometers (value 1500).
    MAXIMUM_WAVELENGTH : float
        The maximum wavelength of the laser in nanometers (value 1630).
    SWEEP_OFF : int
        Constant to compare against the value of :py:func:`sweep_status` (value 0).
    SWEEP_RUNNING : int 
        Constant to compare against the value of :py:func:`sweep_status` (value 1).
    SWEEP_PAUSED : int
        Constant to compare against the value of :py:func:`sweep_status` (value 2).
    SWEEP_TRIGGER_WAIT : int
        Constant to compare against the value of :py:func:`sweep_status` (value 3).
    SWEEP_JUMP : int
        Constant to compare against the value of :py:func:`sweep_status` (value 4).
    """

    # continuous, two-way, external trigger, constant frequency interval
    SWEEP_MODE_MAP = {
        (True, False, False, False): 1,
        (True, True, False, False): 2,
        (False, False, False, False): 3,
        (False, True, False, False): 4,
        (False, False, False, True): 5,
        (False, True, False, True): 6,
        (True, False, True, False): 7,
        (True, True, True, False): 8,
        (False, False, True, False): 9,
        (False, True, True, False): 10,
        (False, False, True, True): 11,
        (False, True, True, True): 12
    }
    SWEEP_MODE_MAP_REV = {num: settings for settings, num in SWEEP_MODE_MAP.items()}

    # Sweep mode statuses
    SWEEP_OFF = 0
    SWEEP_RUNNING = 1
    SWEEP_PAUSED = 2
    SWEEP_TRIGGER_WAIT = 3
    SWEEP_JUMP = 4

    MINIMUM_WAVELENGTH = 1500
    MAXIMUM_WAVELENGTH = 1630


    @staticmethod
    def detect_devices(self) -> List[Dict[str, Any]]:
        """
        Finds and returns all information needed to connect to the device.

        Returns
        -------
        List[Dict[str, Any]]
            Each item in the list contains a dictionary for a unique laser.
            A dictionary from the list can be passed to ``connect()`` to
            connect to the laser. If no device is detected, an empty list 
            is returned.
        """
        device_info = []
        for port in list_ports.comports():
            if port.manufacturer == "Santec Corp.":
                location = port.device
                device_info.append({"address": location})

        return device_info


    def connect(self, address: str="", baudrate: int=9600, terminator: str="\r", timeout: int=100, query_delay: float=0.05) -> bool:
        """
        Connects to and initializes the laser. All parameters are keyword arguments.

        Parameters
        ----------
        address : str
            Address is the serial port the laser is connected to (default "").
        baudrate : int, optional
            Baudrate can be set on the device (default 9600).
        terminator : str, optional
            The string that marks the end of a command (default "\\\\r").
        timeout : int, optional
            The number of seconds to timeout after no response (default 100).
        query_delay : float, optional
            A delay, in seconds, between consecutive write and read operations
            in a query (default 0.05).

        Returns
        -------
        bool
            True if the device has been successfuly connected to. False otherwise.
        """
        log.debug("Entering connect()")
        self.device = serial.Serial(address, baudrate=baudrate, timeout=timeout)
        self.device.flushInput()
        self.device.flushOutput()
        self.query_delay = query_delay

        # Python 3: convert to bytes
        self.terminator = terminator.encode("ASCII")

        # Make sure the shutter is on
        #self.is_on = True
        self.query("SU")
        shutter = self.close_shutter()

        # Set power management to auto
        self.power_control = "auto"
        self.power_auto()

        # Set sweep mode to continuous, two-way, trigger off
        self.sweep_set_mode()

        log.info(f"Connected to laser at {address}")
        return self.device.is_open

    def close(self) -> None:
        """
        Closes the serial connection to the laser.
        """
        log.info("Closing connection to laser")
        self.device.close()
        # TODO: Do we want to delete self.device?

    def write(self, command: str) -> None:
        """
        Write a command to the TSL550.

        Parameters
        ----------
        command : str
            The command to be written as a string. This function automatically
            encodes it using the ASCII standard.
        """
        # Convert to bytes (Python 3)
        command = command.encode("ASCII")

        # Write the command
        self.device.write(command + self.terminator)

    def read(self) -> str:
        """
        Reads a response from the TSL550.

        Returns
        -------
        str
            The response from the laser as a string.
        """
        # Read response
        response = ""
        in_byte = self.device.read()
        while in_byte != self.terminator:
            response += in_byte.decode("ASCII")
            in_byte = self.device.read()

        return response

    def query(self, command, query_delay=None) -> str:
        """
        Write a command to the TSL550. Returns the response (if any).

        Parameters
        ----------
        command : str
            The VISA command to send to the device.
        query_delay : float, optional
            The query delay to use between write and read operations. If None, 
            defaults to ``self.query_delay`` (can be set in ``__init__``). 
            Default is None.

        Returns
        -------
        str
            The response of the query, if any, as a string.
        """
        self.write(command)
        time.sleep(query_delay if query_delay is not None else self.query_delay)
        response = self.read()

        return response

    def _set_var(self, name: str, precision: int, val: float) -> float:
        """
        Generic function to send a laser command with a floating-point variable.

        Parameters
        ----------
        name : str
            The name of the command to send.
        precision : int
            The number of digits to the right of the decimal point.
        val : float
            The value to send to the laser.

        Returns
        -------
        float
            The response from the laser.
        """
        if val is not None:
            command = ("{}{:."+str(precision)+"f}").format(name, val)
        else:
            command = name

        response = self.query(command)
        return float(response)

    def ident(self):
        """
        Query the device to identify itself.

        Places strings of device information such as the name, firmware, and 
        version in the output queue, which is subsequently read and returned.

        | Output format is a string:
        | SANTEC,TSL-550,########,****.****  
        | # field = serial number of the device in 8 digits.  
        | * field = firmware version as 4 digits + .(period) + 4 digits.  

        Returns
        -------
        str
            Result of the identification query.

        Examples
        --------
        >>> laser.ident()
        'SANTEC,TSL-550,06020001,0001.0000'
        """
        log.info("Sending IDENT to laser")
        return self.query('*IDN?')

    def on(self) -> None:
        """
        Turns on the laser diode.
        """
        log.info("Turning on laser")
        self.is_on = True
        self.query("LO")

    def off(self) -> None:
        """
        Turns off the laser diode.
        """
        log.info("Turning off laser")
        self.is_on = False
        self.query("LF")

    def wavelength(self, val: float=None) -> float:
        """
        Sets the output wavelength, and returns nothing. 
        
        If a value is not specified, returns the currently set wavelength. The 
        wavelength value is in nanometers. The minimum step size is 0.0001 nm.

        Parameters
        ----------
        val : float, optional
            The wavelength the laser will be set to in nanometers.

        Returns
        -------
        float
            The currently set wavelength, in nanometers.

        Examples
        --------
        You can get the current wavelength by calling without arguments.

        >>> laser.wavelength()
        1630.0

        The following sets the output wavelength to 1560.123 nanometers.

        >>> laser.wavelength(1560.123)
        """
        if val is not None:
            log.info(f"Setting wavelength to {val} nm")
            self._set_var("WA", 4, val)
            return
        else:
            return self._set_var("WA", 4, val)

    def frequency(self, val: float=None) -> float:
        """
        Tune the laser to a new frequency.

        If a value is not specified, returns the currently set frequency. The
        frequency is in THz with a minimum step size of 0.00001 THz.

        Parameters
        ----------
        val : float, optional
            The frequency to set the laser to in terahertz.

        Returns
        -------
        float
            The currently set frequency, in terahertz.

        Examples
        --------
        >>> laser.frequency()
        183.92175
        >>> laser.frequency(192.0000)
        """
        if val is not None:
            log.info(f"Setting frequency to {val} THz")
            self._set_var("FQ", 5, val)
            return
        else:
            return self._set_var("FQ", 5, val)

    def power_mW(self, val: float=None) -> float:
        """
        Set the output optical power in milliwatts. 
        
        If a value is not specified, returns the current output power.
        
        The valid range is 0.02 - 20 (mW, typical) with a minimum step of 0.01 (mW).

        Parameters
        ----------
        val : float, optional
            The power to be set on the laser in milliwatts.

        Returns
        -------
        float
            The currently set power, in milliwatts.

        Examples
        --------
        >>> laser.power_mW()
        2e-05
        >>> laser.power_mW(10)
        """
        if val is not None:
            log.info(f"Setting power to {val} mW")
            self._set_var("LP", 2, val)
            return
        else:
            return self._set_var("LP", 2, val)

    def power_dBm(self, val: float=None) -> float:
        """
        Set the output optical power in decibel-milliwatts (dBm). 
        
        If a value is not specified, returns the current power.

        The valid range is -17 to +13 (dBm, typical) with a minimum step of 0.01 (dBm).

        Parameters
        ----------
        val : float, optional
            The power to be set on the laser in decibel-milliwatts.

        Returns
        -------
        float
            The currently set power in decibel-milliwatts.

        Examples
        --------
        You can get the current power by calling without arguments.
        The below code indicates the currently output power is -40 dBm.

        >>> laser.power_dBm()
        -040.000

        The following sets the output optical power to +3 dBm.

        >>> laser.power_dBm(3)
        """
        if val is not None:
            log.info(f"Setting power to {val} dBm")
            self._set_var("OP", 2, val)
            return
        else:
            return self._set_var("OP", 2, val)

    def power_att(self, val: float=None) -> float:
        """
        Sets the internal attenuator value.

        If the parameter is not specified, reads out the value currently set.

        The range for ``val`` is 0 to +30 (dB) with a minimum step of 0.01 (dB).

        Parameters
        ----------
        val : float, optional
            The power to be set on the laser in decibels.

        Returns
        -------
        float
            The currently set power in decibel-milliwatts.

        Examples
        --------
        You can get the current power by calling without arguments.
        The below code indicates the currently output power is -40 dBm.

        >>> laser.power_dBm()
        -040.000

        The following sets the output optical power to +3 dBm.

        >>> laser.power_dBm(3)
        """
        if val is not None:
            log.info(f"Setting power to {val} dBm")
            self._set_var("AT", 2, val)
            return
        else:
            return self._set_var("AT", 2, val)

    def power_auto(self) -> None:
        """
        Turn on automatic power control.

        .. important::
           Shutter must be open to switch power modes.
        """
        log.info("Turning on automatic power control")
        self.power_control = "auto"
        self.query("AF")

    def power_manual(self) -> None:
        """
        Turn on manual power control.
        
        .. important::
           Shutter must be open to switch power modes.
        """
        log.info("Turning on manual power control")
        self.power_control = "manual"
        self.query("AO")

    def sweep_wavelength(self, start: float, stop: float, duration: float, number: int=1,
                         delay: float=0, continuous: bool=True, step_size: float=1,
                         twoway: bool=False, trigger: bool=False) -> None:
        """
        Conduct a sweep between two wavelengths. 

        A convenience function that combines :py:func:`sweep_start_wavelength`,
        :py:func:`sweep_end_wavelength`, :py:func:`sweep_delay`, 
        :py:func:`sweep_speed`, :py:func:`sweep_step_time`, 
        :py:func:`sweep_set_mode`, and :py:func:`sweep_start`.

        Parameters
        ----------
        start : float
            The starting wavelength in nanometers.
        stop : float
            The ending wavelength in nanometers.
        duration : float
            In continuous mode, the duration is interpreted as the time
            for one sweep. In stepwise mode, it is used as the dwell time
            for each step. In both cases it has units of seconds and
            should be specified in 100 microsecond intervals.
        number : int, optional
            The sweep is repeated ``number`` times.
        delay : float, optional
            If delay (in seconds) is specified, there is a pause of
            that duration between each sweep (default 0).
        continuous : bool, optional
            If the parameter continuous is False, then the sweep will be
            conducted in steps of fixed size as set by the ``step_size``
            parameter (in nanometres) (default True).
        step_size : float, optional
            The step size for stepwise sweeps (in nanometres) (default 1).
        twoway : bool, optional
            If the twoway parameter is True then one sweep is considered
            to be going from the start wavelength to the stop wavelength
            and then back to the start; if it is False then one sweep
            consists only of going from the start to the top, and the
            laser will simply jump back to the start wavelength at the
            start of the next sweep (default False).
        trigger : bool, optional
            If the trigger parameter is False then the sweep will execute
            immediately. If it is true, the laser will wait for an
            external trigger before starting (default False).

        Notes
        -----
        An illustration of the different sweep modes:

        .. image:: /_static/images/sweep_modes_wl.svg
           :width: 600px
           :alt: Sweep modes graphic by wavelength
        """
        log.info(f"Performing a wavelength sweep over the range {start}-{stop}nm")
        # Set start and end wavelengths
        self.sweep_start_wavelength(start)
        self.sweep_end_wavelength(stop)

        # Set timing
        self.sweep_delay(delay)
        if continuous: # Calculate speed
            speed = abs(stop - start) / duration

            if twoway: # Need to go twice as fast to go up then down in the same time
                speed *= 2

            self.sweep_speed(speed)
        else: # Interpret as time per step
            self.sweep_step_time(duration)

        self.sweep_set_mode(continuous=continuous, twoway=twoway,
                            trigger=trigger, const_freq_step=False)

        if not self.is_on: # Make sure the laser is on
            self.on()

        self.sweep_start(number)

    def sweep_frequency(self, start: float, stop: float, duration: float, number: int=1,
                        delay: float=0, continuous: bool=True, step_size: float=1,
                        twoway: bool=False, trigger: bool=False) -> None:
        """
        Conduct a sweep between two wavelengths. 

        A convenience function that combines :py:func:`sweep_start_frequency`,
        :py:func:`sweep_end_frequency`, :py:func:`sweep_delay`, 
        :py:func:`sweep_speed`, :py:func:`sweep_step_time`, 
        :py:func:`sweep_set_mode`, and :py:func:`sweep_start`.

        Parameters
        ----------
        start : float
            The starting frequency in terahertz.
        stop : float
            The ending frequency in terahertz.
        duration : float
            In continuous mode, the duration is interpreted as the time
            for one sweep. In stepwise mode, it is used as the dwell time
            for each step. In both cases it has units of seconds and
            should be specified in 100 microsecond intervals.
        number : int, optional
            The sweep is repeated ``number`` times.
        delay : float, optional
            If delay (in seconds) is specified, there is a pause of
            that duration between each sweep (default 0).
        continuous : bool, optional
            If the parameter continuous is False, then the sweep will be
            conducted in steps of fixed size as set by the ``step_size``
            parameter (in terahertz) (default True).
        step_size : float, optional
            The step size for stepwise sweeps (in terahertz) (default 1).
        twoway : bool, optional
            If the twoway parameter is True then one sweep is considered
            to be going from the start frequency to the stop frequency
            and then back to the start; if it is False then one sweep
            consists only of going from the start to the top, and the
            laser will simply jump back to the start frequency at the
            start of the next sweep (default False).
        trigger : bool, optional
            If the trigger parameter is False then the sweep will execute
            immediately. If it is true, the laser will wait for an
            external trigger before starting (default False).

        Notes
        -----
        An illustration of the different sweep modes:

        .. image:: /_static/images/sweep_modes_freq.svg
           :width: 600px
           :alt: Sweep modes graphic by frequency
        """
        log.info(f"Performing a frequency sweep over the range {start}-{stop}THz")
        # Set start and end frequencies
        self.sweep_start_frequency(start)
        self.sweep_end_frequency(stop)

        # Set timing
        self.sweep_delay(delay)
        if continuous: # Calculate speed
            speed = abs(3e8/stop - 3e8/start) / duration # Convert to wavelength

            if twoway: # Need to go twice as fast to go up then down in the same time
                speed *= 2

            self.sweep_speed(speed)
        else: # Interpret as time per step
            self.sweep_step_time(duration)

        self.sweep_set_mode(continuous=continuous, twoway=twoway,
                            trigger=trigger, const_freq_step=not continuous)

        if not self.is_on: # Make sure the laser is on
            self.on()

        self.sweep_start(number)

    def sweep_start(self, num: float=1) -> None:
        """
        Sweep between two wavelengths one or more times. 

        Parameters
        ----------
        num : int, optional
            The number of times to perform the sweep (default is 1).

        See Also
        --------
        sweep_start_wavelength
        sweep_end_wavelength
        sweep_wavelength : 
            Convenience function that wraps wavelength sweep setup and starts the sweep.
        sweep_start_frequency
        sweep_end_frequency
        sweep_frequency : 
            Convenience function that wraps frequency sweep setup and starts the sweep.
        sweep_set_mode
        """
        log.info(f"Starting a sweep with {num} repetitions")
        self.query("SZ{:d}".format(num)) # Set number of sweeps
        self.query("SG") # Start sweeping

    def sweep_pause(self) -> None:
        """
        Pause the sweep.  
        
        When a fast sweep speed is set, pause will not function. 

        See Also
        --------
        sweep_resume : Resumes a paused sweep.
        """
        log.info("Pausing the sweep")
        self.query("SP")

    def sweep_resume(self) -> None:
        """
        Resume a paused sweep.

        See Also
        --------
        sweep_pause : Pauses a sweep.
        """
        log.info("Resuming the sweep")
        self.query("SR")

    def sweep_stop(self, immediate: bool=True) -> None:
        """
        Prematurely quit a sweep. 

        Parameters
        ----------
        immediate : bool
            If ``True``, the sweep will stop at once. If ``False`` and the
            sweep is continuous, the sweep will stop once it reaches
            the end wavelength of its current sweep (the default is ``True``).
        """
        log.info(f"Stopping the sweep")
        if immediate:
            self.sweep_pause()

        self.query("SQ")

    def sweep_status(self) -> int:
        """
        Gets the current condition of the sweeping function. 

        | The status code corresponds to the following:
        | 0: Stop (`TSL550.SWEEP_OFF`)
        | 1: Executing (`TSL550.SWEEP_RUNNING`)
        | 2: Pause (`TSL550.SWEEP_PAUSED`)
        | 3: Awaiting Trigger (`TSL550.SWEEP_TRIGGER_WAIT`)
        |    This means that the sweep has been set to start on 
        |    an external trigger and that trigger has not yet 
        |    been received.
        | 4: Setting to sweep start wavelength (`TSL550.SWEEP_JUMP`)
        |    This means that the laser is transitioning between 
        |    the end of one sweep and the start of the next in 
        |    one-way sweep mode.
        
        Returns
        -------
        status : int
            The status code.

        Examples
        --------
        >>> laser.sweep_status()
        0
        >>> laser.sweep_status() == laser.SWEEP_OFF
        True
        """
        log.debug("Entering sweep_status()")
        return int(self.query("SK"))

    def sweep_set_mode(self, continuous: bool=True, twoway: bool=True, trigger: bool=False, const_freq_step: bool=False) -> None:
        """
        Set the mode of the sweep.

        | Valid sweep operation modes are:
        | 1: Continuous operation, One-way
        | 2: Continuous operation, Two-way
        | 3: Step operation, One-way
        | 4: Step operation, Two-way
        | 5: Step operation, One-way (constant frequency interval)
        | 6: Step operation, Two-way (constant frequency interval)
        | 7: Continuous operation, One-way. Operation is started by trigger signal.
        | 8: Continuous operation, Two-way. Operation is started by trigger signal.
        | 9: Step operation, One-way. Operation is started by trigger signal.
        | 10: Step operation, Two-way. Operation is started by trigger signal.
        | 11: Step operation, One-way (constant frequency interval). Operation is started by trigger signal.
        | 12: Step operation, Two-way (constant frequency interval). Operation is started by trigger signal.

        Parameters
        ----------
        continuous : bool, optional
            Continuous (``True``, default) or stepwise (``False``).
        twoway : bool, optional
            Two-way (``True``, default) or one-directional with reset (``False``).
        trigger : bool, optional
            Start on external trigger (defaults to ``False``).
        const_freq_step : bool, optional
            Constant frequency interval, requires stepwise mode (defaults to ``False``).

        Raises
        ------
        AttributeError
            If the sweep configuration is invalid.
        """
        try:
            mode = TSL550.SWEEP_MODE_MAP[(continuous, twoway, trigger, const_freq_step)]
        except KeyError:
            raise ValueError("Invalid sweep configuration.")

        self.query("SM{}".format(mode))

    def sweep_get_mode(self) -> Dict[str, bool]:
        """
        Return the current sweep configuration as a dictionary. 
        
        See :py:func:`sweep_set_mode` for a description of what the parameters
        mean.

        Returns
        -------
        mode : dict
            A dictionary containing boolean values for the keys `continuous`,
            `twoway`, `trigger`, and `const_freq_step`.

        Examples
        --------
        >>> laser.sweep_get_mode()
        {'continuous': True, 'twoway': True, 'trigger': False, 'const_freq_step': False}
        """
        mode_num = int(self.query("SM"))
        mode_settings = TSL550.SWEEP_MODE_MAP_REV[mode_num]

        return {
            "continuous": mode_settings[0],
            "twoway": mode_settings[1],
            "trigger": mode_settings[2],
            "const_freq_step": mode_settings[3]
        }

    def sweep_speed(self, val: float=None) -> float:
        """
        Set the speed of the continuous sweep, in nm/s. 
        
        If a new value is not provided, the current one will be returned.
        Valid range for sweep speed is 1.0 - 100 nm/s with a minimum step of 0.1 nm/s.

        Parameters
        ----------
        val : float, optional
            The sweep speed of the laser, in nm/s.

        Returns
        -------
        float
            The sweep speed of the laser in nm/s.

        Examples
        --------
        >>> laser.sweep_speed()
        26.0
        >>> laser.sweep_speed(25)
        25.0
        """
        if val:
            log.info(f"Setting sweep speed to {val} nm/s")
        return self._set_var("SN", 1, val)

    def sweep_step_wavelength(self, val: float=None) -> float:
        """
        Set the size of each step in the stepwise sweep. 
        
        If a new value is not provided, the current one will be returned.
        
        The valid range is 0.0001 - 160 (nm) with a minimum step of 0.0001 nm.

        Parameters
        ----------
        val : float, optional
            The step size in the stepwise sweep in nanometers.

        Returns
        -------
        float
            The set step size in a stepwise sweep in nm.

        Examples
        --------
        >>> laser.sweep_step_wavelength()
        1.0
        >>> laser.sweep_step_wavelength(2.2)
        2.2
        """
        if val:
            log.info(f"Setting sweep step size to {val} nm")
        return self._set_var("WW", 4, val)

    def sweep_step_frequency(self, val: float=None) -> float:
        """
        Set the size of each step in the stepwise sweep.
        
        Sets the size of each step in the stepwise sweep when constant
        frequency intervals are enabled. If a new value is not
        provided, the current one will be returned. 
        
        The valid range is 0.00002 - 19.76219 (THz) with a minimum step of 0.00001 (THz).

        Parameters
        ----------
        val : float, optional
            The step size of each step in the stepwise sweep in terahertz.

        Returns
        -------
        float
            The set step size in THz.

        Examples
        --------
        >>> laser.sweep_step_frequency()
        0.1
        >>> laser.sweep_step_frequency(0.24)
        0.24
        """
        if val:
            log.info(f"Setting sweep step size to {val} THz")
        return self._set_var("WF", 5, val)

    def sweep_step_time(self, val: float=None) -> float:
        """
        Set the duration of each step in the stepwise sweep. 
        
        If a new value is not provided, the current one will be returned.

        The valid range is 0 - 999.9 (s) with a minimum step of 0.1 s.

        Parameters
        ----------
        val : float, optional
            The duration of each step in seconds.

        Returns
        -------
        float
            The set duration of each step in seconds.

        Examples
        --------
        >>> laser.sweep_step_time()
        0.5
        >>> laser.sweep_step_time(0.8)
        0.8
        """
        if val:
            log.info(f"Setting sweep step time to {val} s")
        return self._set_var("SB", 1, val)

    def sweep_delay(self, val: float=None) -> float:
        """
        Set the time between consecutive sweeps in continuous mode. 
        
        If a new value is not provided, the current one will be returned.

        The valid range is 0 - 999.9 (s) with a minimum step of 0.1 s.

        Parameters
        ----------
        val : float, optional
            The delay between sweeps in seconds.

        Returns
        -------
        float
            The set delay between sweeps in seconds.

        Examples
        --------
        >>> laser.sweep_delay()
        0.0
        >>> laser.sweep_delay(1.5)
        1.5
        """
        if val:
            log.info(f"Setting sweep delay to {val} s")
        return self._set_var("SA", 1, val)

    def sweep_start_wavelength(self, val: float=None) -> float:
        """
        Sets the start wavelength of a sweep.

        Sets the starting wavelength for subsequent sweeps. If no value
        is specified, the current starting wavelength setting is returned.

        The valid range is 1500 - 1630 (nm) with a minimum step of 0.0001 nm.

        Parameters
        ----------
        val : float, optional
            The starting value of the wavelength sweep in nanometers.

        Returns
        -------
        float
            The current sweep start wavelength in nm.

        Examples
        --------
        >>> laser.sweep_start_wavelength()
        1500.0
        >>> laser.sweep_start_wavelength(1545)
        1545.0
        """
        if val:
            log.info(f"Setting sweep start wavelength to {val} nm")
        return self._set_var("SS", 4, val)

    def sweep_start_frequency(self, val: float=None) -> float:
        """
        Sets the start frequency of a sweep.

        Sets the starting frequency for subsequent sweeps. If no value
        is specified, the current starting frequency setting is returned.

        Minimum step size is 0.00001 THz.

        Parameters
        ----------
        val : float, optional
            The starting value of the frequency sweep in terahertz.

        Returns
        -------
        float
            The current sweep start frequency in THz.

        Examples
        --------
        >>> laser.sweep_start_frequency()
        199.86164
        >>> laser.sweep_start_frequency(196)
        195.99999
        """
        if val:
            log.info(f"Setting sweep start frequency to {val} THz")
        return self._set_var("FS", 5, val)

    def sweep_end_wavelength(self, val: float=None) -> float:
        """
        Sets the end wavelength of a sweep.

        Sets the ending wavelength for subsequent sweeps. If no value
        is specified, the current ending wavelength setting is returned.

        Minimum step size is 0.0001 nm.

        Parameters
        ----------
        val : float, optional
            The ending value of the wavelength sweep in nanometers.

        Returns
        -------
        float
            The current sweep end wavelength in nm.

        Examples
        --------
        >>> laser.sweep_end_wavelength()
        1630.0
        >>> laser.sweep_end_wavelength(1618)
        1618.0
        """
        if val:
            log.info(f"Setting sweep end wavelength to {val} nm")
        return self._set_var("SE", 4, val)

    def sweep_end_frequency(self, val: float=None) -> float:
        """
        Sets the end frequency of a sweep.

        Sets the ending frequency for subsequent sweeps. If no value
        is specified, the current ending frequency setting is returned.

        Minimum step size is 0.00001 THz.

        Parameters
        ----------
        val : float, optional
            The ending value of the frequency sweep in THz.

        Returns
        -------
        float
            The current sweep end frequency in THz.

        Examples
        --------
        >>> laser.sweep_end_frequency()
        183.92175
        >>> laser.sweep_end_frequency(185.5447)
        185.5447
        """
        if val:
            log.info(f"Setting sweep end frequency to {val} THz")
        return self._set_var("FF", 5, val)

    def open_shutter(self) -> None:
        """
        Opens the laser's shutter.
        """
        log.info("Opening laser shutter")
        self.query("SO")

    def close_shutter(self) -> None:
        """
        Closes the laser's shutter.
        """
        log.info("Closing laser shutter")
        self.query("SC")

    def trigger_enable_output(self) -> None:
        """
        Sets ENABLE of the external trigger signal input.

        Use when the laser sweep should be triggered to begin on an external signal.

        See Also
        --------
        trigger_disable_output
        """
        log.info("Enabling external trigger signal input")
        self.query("TRE")

    def trigger_disable_output(self) -> None:
        """
        Sets DISABLE of the external trigger signal input.

        Use when the laser sweep should not be triggered to begin on an external signal.

        See Also
        --------
        trigger_enable_output
        """
        log.info("Disabling external trigger signal input")
        self.query("TRD")

    def trigger_get_mode(self) -> str:
        """
        Reads out the currently set value for the timing of the trigger signal output.

        Returns
        -------
        mode : str
            The mode for the trigger signal output timing; one of "None", 
            "Stop", "Start", or "Step".
        """
        log.debug("Entering trigger_get_mode()")
        current_state = self.query("TM")
        if current_state == 0:
            return "None"
        elif current_state == 1:
            return "Stop"
        elif current_state == 2:
            return "Start"
        elif current_state == 3:
            return "Step"

    def trigger_set_mode(self,val: str=None) -> str:
        """
        Sets the trigger mode.

        The output trigger can be set to fire at the start of a wavelength
        sweep, at the end of a sweep, or at a fixed step.

        Parameters
        ----------
        val : str, opt
            One of: "None", "Stop", "Start", "Step".
        
        Returns
        -------
        str
            The final mode. "Stop", "Start", or "Step"

        Raises
        ------
        ValueError
            If the value is not one of "None", "Stop", "Start", or "Step".

        See Also
        --------
        trigger_set_step
        """
        mode = 0
        if val == "None" or val == None:
            mode = 0
        elif val == "Stop":
            mode = 1
        elif val == "Start":
            mode = 2
        elif val == "Step":
            mode = 3
        else:
            raise ValueError("Invalide output trigger mode supplied. Choose from None, Stop, Start, and Step.")
        current_state = int(self.query("TM{}".format(mode)))
        if current_state == 1:
            return "Stop"
        elif current_state == 2:
            return "Start"
        elif current_state == 3:
            return "Step"

    def trigger_set_step(self, step: float=None) -> float:
        """
        Sets (or returns) the interval of the trigger signal output.

        Valid range is 0.0001 - 160 nm with a minimum step of 0.0001 nm.

        Parameters
        ----------
        step : float
            The interval of the trigger signal output, in nanometers.

        Returns
        -------
        val : float
            The currently set value (returned both on set and on read).

        Examples
        --------
        >>> laser.trigger_set_step()
        0.012
        """
        if step:
            log.info(f"Setting trigger step to {step} nm")
        return self._set_var("TW", 4, val=step)


    def wavelength_logging_number(self) -> int:
        """
        Reads the number of data points recored by wavelength logging.

        Returns
        -------
        int
            A value between 0 and 65535, the number of recorded data points.

        Examples
        --------
        >>> laser.wavelength_logging_number()
        5001
        """
        log.debug("Entering wavelength_logging_number()")
        return int(self.query("TN"))

    def wavelength_logging(self) -> List[float]:
        """
        Read the list of all the wavelength points logged into the laser's buffer. 
        
        Assumes that all the correct sweep and triggering protocol
        are met (see manual page 6-5).

        Returns
        -------
        points : list
            A Python list of length :py:func:`wavelength_logging_number`. Each
            item in the list has units of nanometers.

        Raises
        ------
        RuntimeError
            If reading the wavelength logging buffer fails.

        Examples
        --------
        >>> laser.wavelength_logging_number()
        417
        >>> wl = laser.wavelength_logging()
        >>> len(wl)
        417
        >>> type(wl)
        <class 'list'>
        >>> wl[0]
        1675.0276
        """
        log.debug("Entering wavelength_logging()")
        # stop laser from outputting
        self.query("SU")

        # First, get the number of wavelength points
        num_points = self.wavelength_logging_number()

        # Preallocate arrays
        wavelength_points = []

        # Now petition the laser for the wavelength points
        self.write("TA")
        time.sleep(0.1)

        # Iterate through wavelength points
        for nWave in range(int(num_points)):
            while True:
                try:
                    # A data is in 4-byte binary, and transmitted in Big endians
                    in_byte = self.device.read(4)
                    # Data format is integer number in 0.1 pm units
                    current_wavelength = float(struct.unpack(">I", in_byte)[0]) / 1e4
                    break
                except:
                    raise RuntimeError("Error reading wavelength data from laser")

            wavelength_points.append(current_wavelength)

        # stop laser from outputting
        self.query("SU")
        return wavelength_points

    def status(self, verbose: bool=False) -> str:
        """
        Query the status of the laser and print its results.

        Parameters
        ----------
        verbose : bool, optional
            If True, print the string status of each parameter (default False).

        Returns
        -------
        code : str
            A status code for the status of the laser. 

        The following example shows the laser as on and all operations as complete.

        Notes
        -----
        The status code is a 7-character 
        string status comprising a code and 6 digits (with positions represented
        as '-654321'), interpreted as follows:

        | Code [-/none]: Laser diode (LD) status
        |     '-': ON
        |     none: OFF
        | 6th digit [0/1]: Coherence control
        |     0: OFF
        |     1: ON
        | 5th digit [0/1]: Fine-tuning
        |     0: OFF
        |     1: ON
        | 4th digit [0-5]: Control mode of output power, attenuator, and power
        |     monitor range, according to the following table:

        .. table::
   
           ===== ============= ================== ===========================
           Value Power control Attenuator control Power monitor range control
           ===== ============= ================== ===========================
           0     Auto          Hold               Auto
           1     Manual        Hold (Manual)      Auto
           2     Auto          Auto               Auto
           4     Auto          Hold               Hold
           5     Manual        Hold (Manual)      Hold
           ===== ============= ================== ===========================

        | 3rd digit [0/1]: Laser diode temperature error
        |     0: No error
        |     1: Error occurred
        | 2nd digit [0/1]: Laser diode current limit error
        |     0: No error
        |     1: Error occurred
        | 1st digit [0-7]: Operation status
        |     0: Operation is completed
        |     1: Wavelength is tuning
        |     2: Laser diode current is setting (LD is on state and power control is Auto)
        |     3: Wavelength is tuning and LD current is setting
        |     4: Attenuator is setting
        |     5: Wavelength is setting and attenuator is setting
        |     6: LD current is setting and attenuator is setting
        |     7: Wavelength is tuning, LD current is setting, and attenuator is setting

        Examples
        --------
        >>> laser.status()
        '-011000'
        """
        log.debug("Entering status()")
        status = self.query("SU")

        # Check if LD is on
        self.is_on = True if int(status) < 0 else False

        if not verbose:
            return status
        else:
            code = {    '-' : "'-': ON\n",
                        ' ' : "none: OFF\n"
            }
            digit_6 = { '0' : "Coherence control: OFF\n",
                        '1' : "Coherence control: ON\n"
            }
            digit_5 = { '0' : "Fine-tuning: OFF\n",
                        '1' : "Fine-tuning: ON\n"
            }
            digit_4 = { '0' : "Power Control: Auto\nAttenuator Control: Hold\nPower Monitor Range Control: Auto\n",
                        '1' : "Power Control: Manual\nAttenuator Control: Hold (Manual)\nPower Monitor Range Control: Auto\n",
                        '2' : "Power Control: Auto\nAttenuator Control: Auto\nPower Monitor Range Control: Auto\n",
                        '3' : "4th digit is not specified for a value of 3\n",
                        '4' : "Power Control: Auto\nAttenuator Control: Hold\nPower Monitor Range Control: Hold\n",
                        '5' : "Power Control: Manual\nAttenuator Control: Hold (Manual)\nPower Monitor Range Control: Hold\n",
            }
            digit_3 = { '0' : "Laser diode temperature error: No error\n",
                        '1' : "Laser diode temperature error: Error occurred\n",
            }
            digit_2 = { '0' : "Laser diode current limit error: No error\n",
                        '1' : "Laser diode current limit error: Error occurred\n"
            }
            digit_1 = { '0' : "Operation status: Operation is completed\n",
                        '1' : "Operation status: Wavelength is tuning\n",
                        '2' : "Operation status: Laser diode current is setting (LD is on state and power control is Auto)\n",
                        '3' : "Operation status: Wavelength is tuning and LD current is setting\n",
                        '4' : "Operation status: Attenuator is setting\n",
                        '5' : "Operation status: Wavelength is setting and attenuator is setting\n",
                        '6' : "Operation status: LD current is setting and attenuator is setting\n",
                        '7' : "Operation status: Wavelength is tuning, LD current is setting, and attenuator is setting\n"
            }
            output = status + code[status[0]] + digit_6[status[1]] \
                + digit_5[status[2]] + digit_4[status[3]] + digit_3[status[4]] \
                + digit_2[status[5]] + digit_1[status[6]]
            return output
