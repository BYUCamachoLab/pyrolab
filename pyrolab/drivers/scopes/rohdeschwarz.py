# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Rohde & Schwarz Digital Oscilloscopes
-------------------------------------

Submodule containing drivers for each supported laser type.

As stated in the manual (see docs/RTO_UserManaul_en_11.pdf), the following
scopes should be supported:

This manual describes the following R&S®RTO models with firmware version 3.70:
   - R&S®RTO2002 (1329.7002K02)
   - R&S®RTO2004 (1329.7002K04)
   - R&S®RTO2012 (1329.7002K12)
   - R&S®RTO2014 (1329.7002K14)
   - R&S®RTO1024 (1316.1000K24)
   - R&S®RTO2022 (1329.7002K22)
   - R&S®RTO2024 (1329.7002K24)
   - R&S®RTO2032 (1329.7002K32)
   - R&S®RTO2034 (1329.7002K34)
   - R&S®RTO2044 (1329.7002K44)
   - R&S®RTO2064 (1329.7002K64)
   - R&S®RTO1002 (1316.1000K02)
   - R&S®RTO1004 (1316.1000K04)
   - R&S®RTO1012 (1316.1000K12)
   - R&S®RTO1014 (1316.1000K14)
   - R&S®RTO1022 (1316.1000K22)
   - R&S®RTO1044 (1316.1000K44)

If you don't have the NI VISA implementation installed on your computer, be 
sure to install the separate dependency ``pyvisa-py``, which is not included
with PyroLab.
"""

import time

import deprecation
import pyvisa as visa

from pyrolab import __version__
from pyrolab.drivers.scopes import Scope, VISAResourceExtentions

class RTO(Scope):
    """
    Simple network controller class for R&S RTO oscilloscopes.

    Parameters
    ----------
    address : str
        The IP address of the instrument.
    interface : str, optional
        The interface to use to connect to the instrument. May be one
        of "TCPIP", "GPIB", "ASRL", etc. Default is "TCPIP".
    protocol : str, optional
        The protocol to use for the LAN connection. Can be "INSTR"
        or "hislip". Default is "hislip".
    timeout : int, optional
        The device response timeout in milliseconds (default infinite).
    """
    def __init__(self, address, interface="TCPIP", protocol="hislip", timeout=None):
        rm = visa.ResourceManager()
        self.device = rm.open_resource("{}::{}::{}".format(interface, address, protocol))
        self.device.timeout = timeout
        self.write_termination = ''
        self.device.ext_clear_status()
        
        # print("Connected: {}".format(self.device.query('*IDN?')))
        self.write('*RST;*CLS')
        self.write('SYST:DISP:UPD ON')
        self.device.ext_error_checking()

    @property
    def timeout(self):
        return self.device.timeout

    @timeout.setter
    def timeout(self, ms):
        self.device.timeout = ms

    def query(self, message, delay=None):
        """
        A combination of :py:func:`write(message)` and :py:func:`read()`.

        Parameters
        ----------
        message : str
            The message to send.
        delay : float, optional
            Delay in seconds between write and read operations. If None,
            defaults to `self.device.query_delay`.
        """
        self.device.query(message, delay)

    def write(self, message, termination=None, encoding=None):
        """
        Writes a message to the scope.

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

    def write_block(self, message):
        """
        Writes a message to the scope, waits for it to complete, and checks for errors.

        Parameters
        ----------
        message : str
            The message to send.

        Notes
        -----
        This function is blocking.
        """
        self.write(message)
        self.wait_for_device()
        self.device.ext_error_checking()

    @deprecation.deprecated(deprecated_in="0.1.0", removed_in="0.2.0",
                current_version=__version__,
                details="Use 'write_block()' instead.")
    def __send_command(self, command):
        """
        Writes a message to the scope, waits for it to complete, and checks for errors.

        Warning
        -------
        .. deprecated:: 0.1.0
           :py:func:`__send_command` will be removed in 0.2.0, it is replaced by
           :py:func:`write_block` beginning in 0.1.0.

        Parameters
        ----------
        command : str
            The message to send.

        Notes
        -----
        This function is blocking.
        """
        self.device.write(command)
        self.wait_for_device()
        self.device.ext_error_checking()

    def wait_for_device(self):
        """
        Waits for the device until last action is complete.

        Notes
        -----
        This function is blocking.
        """
        self.device.query('*OPC?')

    def acquisition_settings(self, sample_rate, duration, force_realtime=False):
        """
        Sets the scope acquisition settings.

        The exact command this executes is:
        `'ACQ:POIN:AUTO RES;:ACQ:SRAT {};:TIM:RANG {}'`

        Parameters
        ----------
        sample_rate : float
            Sample rate of device.
        duration : float
            Length of acquisition in seconds.
        force_realtime : bool, optional
            Defaults to False.
        """
        short_command = 'ACQ:POIN:AUTO RES;:TIM:RANG {}'.format(duration)
        if force_realtime:
            self.write_block('ACQ:MODE RTIM')
        self.write_block(short_command)

    def set_channel(self, channel, state="ON", coupling="DCLimit", range=0.5, position=0, offset=0, invert="OFF"):
        """
        Configures a channel.

        Parameters
        ----------
        channel : int
            The channel number to be added.
        state : str, optional
            Switches the channel signal on or off. Acceptable values are ``ON``
            and ``OFF``. Default is ``ON`` (see ``CHANnel<m>:STATe``).
        coupling : str, optional
            Selects the connection of the indicated channel signal. Valid values are
            "DC" (direct connection with 50 ohm termination), "DCLimit" (direct connection 
            with 1M ohm termination), or "AC" (connection through DC capacitor).
            Default is DCLimit (see ``CHANnel<m>:COUPling``).
        range : float, optional
            Sets the voltage range across the 10 vertical divisions of the diagram
            in V/div. Default is 0.5 (see ``CHANnel<m>:RANGe``).
        position : float, optional
            Sets the vertical position of the indicated channel as a graphical value.
            Valid range is [-5, 5] in increments of 0.01 (units is "divisions").
            Default is 0 (see ``CHANnel<m>:POSition``).
        offset : float, optional
            The offset voltage is subtracted to correct an offset-affected signal. 
            The offset of a signal is determined and set by the autoset procedure.
            Default value is 0 (see ``CHANnel<m>:OFFSet``).
        invert : str, optional
            Turns the inversion of the signal amplitude on or off. To invert means 
            to reflect the voltage values of all signal components against the ground 
            level. If the inverted channel is the trigger source, the instrument 
            triggers on the inverted signal. Acceptable values are "ON" or "OFF".
            Default is "OFF" (see ``CHANnel<m>:INVert``).
        """
        cmd = 'CHAN{}:STAT {}; COUP {};RANG {};POS {};OFFS {}; INV {}'.format(
            channel, state, coupling, range, position, offset, invert
        )
        self.write_block(cmd)

    @deprecation.deprecated(deprecated_in="0.1.0", removed_in="0.2.0",
                current_version=__version__,
                details="Use 'set_channel()' instead.")
    def add_channel(self, channel_num, range, position = 0, offset = 0, coupling = "DCL"):
        """Add a channel.
        
        Warning
        -------
        .. deprecated:: 0.1.0
           :py:func:`add_channel` will be removed in 0.2.0, it is replaced by
           :py:func:`set_channel` beginning in 0.1.0.
        """
        short_command = 'CHAN{}:RANG {};POS {};OFFS {};COUP {};STAT ON'.format(
            channel_num, range, position, offset, coupling
        )
        self.__send_command(short_command)

    def __add_trigger(self,
        type,
        source,
        source_num,
        level,
        trigger_num = 1,
        mode = "NORM",
        settings: str = ""
    ):
        short_command = 'TRIG{}:MODE {};SOUR {};TYPE {};LEV{} {};'.format(
        trigger_num, mode, source, type, source_num, level
    )
        #Add a trigger.
        self.write_block(short_command + settings)

    def edge_trigger(self, channel, voltage):
        """
        Add an edge trigger to the specified channel.

        Parameters
        ----------
        channel : int
            The channel to configure as a trigger.
        voltage : float
            Voltage threshold for positive slope edge trigger.
        """
        #Todo: Edit to allow other trigger sources (ex. External Trigger).
        self.__add_trigger(
            type = "EDGE",
            source = "CHAN{}".format(channel),
            source_num = channel,
            level = voltage,
            settings = "EDGE:SLOP POS"
        )

    def acquire(self, run='single'):
        """
        Asynchronous command that starts acquisition.

        Parameters
        ----------
        run : str
            Specifies the type of run. Allowable values are ``continuous`` 
            (starts the continuous acquisition), ``single`` (starts a defined
            number of acquisition cycles as set by 
            :py:func:``acquisition_settings()``), or ``stop`` (stops a 
            running acquisition). Default is ``single``.
        """        
        if run == "single":
            cmd = "SING"
        elif run == "continuous":
            cmd = "RUN"
        elif run == "stop":
            cmd = "STOP"
        else:
            raise ValueError("%s is not a valid argument" % run)
        
        self.write(cmd)

    @deprecation.deprecated(deprecated_in="0.1.0", removed_in="0.2.0",
                current_version=__version__,
                details="Use 'acquire()' instead.")
    def start_acquisition(self, timeout, type='SING'):
        """
        Asynchronous command that starts acquisition.

        Warning
        -------
        .. deprecated:: 0.1.0
           :py:func:`start_acquisition` will be removed in 0.2.0, it is replaced by
           :py:func:`acquire` beginning in 0.1.0.

        Parameters
        ----------
        timeout : int
            The timeout in seconds for all I/O operations.
        run : str
            Specifies the type of run. Allowable values are ``continuous`` 
            (starts the continuous acquisition), ``single`` (starts a defined
            number of acquisition cycles as set by ``acquisition_settings()``),
            or ``stop`` (stops a running acquisition). Default is ``single``.
        """        
        # Translate seconds to ms.
        self.device.timeout = timeout * 1000
        if type not in ["SING", "RUN", "STOP"]:
            raise ValueError("%s is not a valid argument" % type)            
        
        self.write(type)

    def get_data(self, channel, form="ascii"):
        """
        Retrieves waveform data from the specified channel in the specified 
        data type.

        Parameters
        ----------
        channel : int
            The channel to retrieve data for.
        form : str, optional
            The data format used for the transmission of waveform data. 
            Allowable values are ``ascii``, ``real``, ``int8``, and ``int16``.
            Default is ``ascii``.

        See Also
        --------
        RTO User Manual, commands for ``FORMat[:DATA]`` and 
        ``CHANnel<m>[:WAVeform<n>]:DATA[:VALues]?``
        """
        if form == "ascii":
            fmt = "ASC"
        elif form == "real":
            fmt = "REAL,32"
        elif form == "int8":
            fmt = "INT,8"
        elif form == "int16":
            fmt = "INT,16"
        else:
            raise ValueError("unexpected value '%s' for argument 'form'." % form)

        cmd = 'FORM {};:CHAN{}:DATA?'.format(fmt, channel)
        
        if form == "ascii":
            return self.device.query_ascii_values(cmd)
        elif form == "real":
            return self.device.query_binary_values(cmd)
        else:
            return self.query(cmd)

    @deprecation.deprecated(deprecated_in="0.1.0", removed_in="0.2.0",
                current_version=__version__,
                details="Use 'get_data()' instead.")
    def get_data_ascii(self, channel):
        """
        Get the data in ascii encoding.

        Warning
        -------
        .. deprecated:: 0.1.0
           :py:func:`get_data_ascii` will be removed in 0.2.0, it is replaced by
           :py:func:`get_data` beginning in 0.1.0.
        """
        dataQuery = 'FORM ASC;:CHAN{}:DATA?'.format(channel)
        waveform = self.device.query_ascii_values(dataQuery)
        return waveform

    @deprecation.deprecated(deprecated_in="0.1.0", removed_in="0.2.0",
                current_version=__version__,
                details="Use 'get_data()' instead.")
    def get_data_binary(self, channel):
        """
        Get the data in binary encoding.

        Warning
        -------
        .. deprecated:: 0.1.0
           :py:func:`get_data_binary` will be removed in 0.2.0, it is replaced by
           :py:func:`get_data` beginning in 0.1.0.
        """
        dataQuery = 'FORM REAL;:CHAN{}:DATA?'.format(channel)
        waveform = self.device.query_binary_values(dataQuery)
        return waveform

    def screenshot(self, path):
        """
        Takes a screenshot of the scope and saves it to the specified path.

        Image format is PNG.

        Parameters
        ----------
        path : str
            The local path, including filename and extension, of where
            to save the file.
        """
        instrument_save_path = "'C:\\temp\\Last_Screenshot.png\'"
        self.write('HCOP:DEV:LANG PNG')
        self.write('MMEM:NAME {}'.format(instrument_save_path))
        self.write('HCOP:IMM')
        self.wait_for_device()
        self.device.ext_error_checking()
        self.device.ext_query_bin_data_to_file(
            'MMEM:DATA? {}'.format(instrument_save_path),
            str(path)
        )
        self.device.ext_error_checking()

    @deprecation.deprecated(deprecated_in="0.1.0", removed_in="0.2.0",
                current_version=__version__,
                details="Use 'screenshot()' instead.")
    def take_screenshot(self, path):
        """
        Takes a screenshot of the scope and saves it to the specified path.

        Image format is PNG.

        Warning
        -------
        .. deprecated:: 0.1.0
           :py:func:`take_screenshot` will be removed in 0.2.0, it is replaced by
           :py:func:`screenshot` beginning in 0.1.0.

        Parameters
        ----------
        path : str
            The local path, including filename and extension, of where
            to save the file.
        """
        instrument_save_path = '\'C:\\temp\\Last_Screenshot.png\''
        self.device.write('HCOP:DEV:LANG PNG')
        self.device.write('MMEM:NAME {}'.format(instrument_save_path))
        self.device.write('HCOP:IMM')
        self.wait_for_device()
        self.device.ext_error_checking()
        self.device.ext_query_bin_data_to_file(
            'MMEM:DATA? {}'.format(instrument_save_path),
            str(path)
        )
        self.device.ext_error_checking()

class RemoteDisplay:
    def __init__(self, scope: RTO):
        self.scope = scope
        