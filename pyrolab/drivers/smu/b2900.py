# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Keysight B2900/BL series SMU
=====================================

.. admonition:: Dependencies
   :class: note

   | pyvisa
   | NI-VISA *or* pyvisa-py
"""

import time

import pyvisa as visa

from pyrolab import __version__
from pyrolab.drivers.smu import SMU, VISAResourceExtentions


class B2900(SMU):
    """
    Simple network controller class for Keysight B2900 SMU.

    This class is used to control the Keysight B2900B/BL SMU. These are not local
    devices, nor native PyroLab objects. Therefore, network device 
    autodetection is not supported.
    """
    
    @staticmethod
    def detect_devices():
        """
        Network device detection not supported.
        
        Becuase SMUs are connected to using the IP address,
        this function does not detect them and instead always returns an empty 
        list.
        """
        device_info = []
        return device_info

    def connect(self, address: str="", timeout: float=1e3) -> bool:
        """
        Connects to and initializes the SMU.

        Parameters
        ----------
        address : str
            The IP address of the instrument.
        timeout : int, optional
            The device response timeout in milliseconds (default 1 ms).
            Pass ``None`` for infinite timeout.
        """
        rm = visa.ResourceManager()
        self.device = rm.open_resource(f"TCPIP0::{address}::5025::SOCKET")
        self.device.timeout = timeout
        self.device.read_termination = '\n'
        self.write_termination = '\n'
        self.device.ext_clear_status()
        
        self.write('*RST;*CLS')
        self.write(':DISP:ENAB ON')
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

    def query(self, message: str="", delay: float=None):
        """
        A combination of :py:func:`write` and :py:func:`read`.

        Parameters
        ----------
        message : str
            The message to send.
        delay : float, optional
            Delay in seconds between write and read operations. If None,
            defaults to ``self.device.query_delay``.
            
        Raises
        ------
        VI_ERROR_TMO
            If there is no data to be read
        """
        return self.device.query(message, delay)

    def write(self, message: str, termination: str=None, encoding: str=None):
        """
        Writes a message to the SMU.

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
    
    def screenshot(self, path: str, form: str='PNG'):
        """
        Takes a screenshot of the scope and saves it to the specified path.

        Image format is PNG.

        Parameters
        ----------
        path : str
            The local path, including filename and extension, of where
            to save the file.
        form : str, optional
            Format of the created image. Defaults to PNG. Can be JPG, BMP, PNG, or WMF.
        """
        instrument_save_path = "'C:\\temp\\Last_Screenshot.png\'"
        self.write(f'HCOP:SDUM:FORM {form}')
        self.wait_for_device()
        self.device.ext_error_checking()
        self.device.ext_query_bin_data_to_file('HCOP:SDUM:DATA?', str(path))
        self.device.ext_error_checking()
        
    def write_block(self, message: str):
        """
        Writes a message to the scope, waits for it to complete, and checks for errors.

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

        .. note::
           This function is blocking.
        """
        self.device.ext_wait_for_opc()
    
    #measure_ and sweep_ not tested yet
    def measure_current(self, voltage: float, compliance: float, power_line_cycles: int=2, channel: int=0):
        """
        Performs a spot measurement of current at the speficied voltage
        
        Parameters
        ----------
        voltage : float
            Voltage in Volts
        compliance : float
            Safety limit on current, in Amps
        power_line_cycles : int, optional
            Duration of measurement in terms of power line cycles, defaults to 2
        channel : int, optional
            Channel number, defaults is 1
        """
        if channel == 0:
            channel = ""

        #resets device
        self.write("*RST")
        
        #sets source mode to current
        self.write(f":SOUR{channel}:FUNC:MODE VOLT")
        #sets current
        self.write_block(f":SOUR{channel}:VOLT {voltage}")
        #sets output protection (current limit)
        self.write(f":SENS{channel}:CURR:PROT {compliance}")
        #sets measurement range to auto
        self.write(f":SENS{channel}:CURR:RANG:AUTO ON")
        #turns on voltage sensor
        self.write(f":SENS{channel}:FUNC \"CURR\"")
        #sets measurement speed (aperture time)
        self.write(f":SENS:CURR:NPLC {power_line_cycles}")
        
        self.device.ext_error_checking()
        
        #turns on source and measurement channel
        self.write(":OUTP ON")
        #takes measurement
        measurement = self.query(":MEAS:CURR? " + (f"(@2)" if channel == 2 else "(@1)"))
        #turns off voltage and measurement channel
        self.write(":OUTP OFF")
        
        self.device.ext_error_checking()
        return measurement
    
    def measure_voltage(self, current: float, compliance: float, power_line_cycles: int=2, channel: int=0):
        """
        Performs a spot measurement of voltage at the specified current
        
        Parameters
        ----------
        current : float
            Current in Amps
        compliance : float
            Safety limit on voltage, in Volts
        power_line_cycles : int, optional
            Duration of measurement in terms of power line cycles, defaults to 2
        channel : int, optional
            Channel number, default is 1
        """
        if channel == 0:
            channel = ""
        
        #resets device
        self.write("*RST")
        
        #sets source mode to current
        self.write(f":SOUR{channel}:FUNC:MODE CURR")
        #sets current
        self.write_block(f":SOUR{channel}:CURR {current}")
        
        #turns on voltage sensor
        self.write(f":SENS{channel}:FUNC \"VOLT\"")
        #sets output protection (voltage limit)
        self.write(f":SENS{channel}:VOLT:PROT {compliance}")
        #sets measurement range to auto
        self.write(f":SENS{channel}:VOLT:RANG:AUTO ON")
        #sets measurement speed (aperture time)
        self.write(f":SENS{channel}:VOLT:NPLC {power_line_cycles}")
        
        self.device.ext_error_checking()
        
        #turns on source and measurement channel
        self.write(":OUTP ON")
        #takes measurement
        measurement = self.query(":MEAS:VOLT? " + (f"(@2)" if channel == 2 else "(@1)"))
        #turns off current source and measurement channel
        self.write(":OUTP OFF")
        
        self.device.ext_error_checking()
        return measurement
    
    def toggle_colors(self):
        """
        Toggles color scheme of SMU display
        """
        color = self.query(":DISP:CSET?")
        self.write(":DISP:CSET " + str(int(color) % 2 + 1))

    #def sweep_voltage(self, start, stop, steps, compliance, measurement_speed, channel="", log=False):
        """
        Staircase sweep measurement of current
        
        Parameters
        ----------
        start : float
            Starting voltage
        stop : float
            Finish voltage
        steps : int
            Number of steps in meaurement
        compliance : float
            Sets current limit
        measurement_speed : float
            Aperture speed in seconds
        channel : int, optional
            Channel number, defaults to 1
        log : bool, optional
            Use logarithmic sweep spacing. Defaults to linear
        """
        """
        #resets device
        self.write("*RST")
        #Set sweep source
        self.write(f":SOUR{channel}:FUNC:MODE VOLT")
        self.write(f":SOUR{channel}:VOLT:MODE SWE")
        self.write(f":SOUR:SWE:SPAC " + ("LOG" if log else "LIN"))
        self.write(f":SOUR{channel}:VOLT:STAR {start}")
        self.write(f":SOUR{channel}:VOLT:STOP {stop}")
        self.write(f":SOUR{channel}:VOLT:POIN {steps}")
        
        #set measurement
        self.write(f":SENS{channel}:FUNC \"CURR\"")
        self.write(f":SENS{channel}:CURR:APER {measurement_speed}")
        self.write(f":SENS{channel}:CURR:PROT {compliance}")
        
        #generate triggers
        self.write(":TRIG:SOUR AINT")
        self.write(f":TRIG:COUN {steps}")
        
        self.device.ext_error_checking()
        
        #enable output
        self.write(":OUTP ON")
        
        #begin measurement
        self.write_block(":INIT" + (f" (@2)" if channel == 2 else " (@1)"))
        #turn off output
        self.write(":OUTP OFF")
        
        #read data
        measurement = self.query(":FETC:ARR:CURR? " + (f"(@2)" if channel == 2 else "(@1)"))
        
        self.device.ext_error_checking()
        
        return measurement
        """
    #def sweep_current(self, start, stop, steps, compliance, measurement_speed, channel="", log=False):
        """
        Staircase sweep measurement of voltage
        
        Parameters
        ----------
        start : float
            Starting current
        stop : float
            Finish current
        steps : int
            Number of steps in meaurement
        compliance : float
            Sets voltage limit
        measurement_speed : float
            Aperture speed in seconds
        channel : int, optional
            Channel number, defaults to 1
        log : bool, optional
            Use logarithmic sweep spacing. Defaults to linear
        """
        """
        #resets device
        self.write("*RST")
        #Set sweep source
        self.write(f":SOUR{channel}:FUNC:MODE CURR")
        self.write(f":SOUR{channel}:CURR:MODE SWE")
        self.write(f":SOUR:SWE:SPAC " + ("LOG" if log else "LIN"))
        self.write(f":SOUR{channel}:CURR:STAR {start}")
        self.write(f":SOUR{channel}:CURR:STOP {stop}")
        self.write(f":SOUR{channel}:CURR:POIN {steps}")
        
        #set measurement
        self.write(f":SENS{channel}:FUNC \"VOLT\"")
        self.write(f":SENS{channel}:VOLT:APER {measurement_speed}")
        self.write(f":SENS{channel}:VOLT:PROT {compliance}")
        
        #generate triggers
        self.write(":TRIG:SOUR AINT")
        self.write(f":TRIG:COUN {steps}")
        
        self.device.ext_error_checking()
        
        #enable output
        self.write(":OUTP ON")
        
        #begin measurement
        self.write_block(":INIT" + (f" (@2)" if channel == 2 else " (@1)"))
        #turn off output
        self.write(":OUTP OFF")
        
        #read data
        measurement = self.query(":FETC:ARR:VOLT? " + (f"(@2)" if channel == 2 else "(@1)"))
        
        self.device.ext_error_checking()
        
        return measurement
`       """
        
