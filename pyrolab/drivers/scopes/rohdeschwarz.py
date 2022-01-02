# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Rohde & Schwarz Digital Oscilloscopes
=====================================

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
with PyroLab. NI VISA is available for Mac, Windows, and Linux.

Common Issues
-------------
1. Note that if a trigger is set and you try to acquire data but end up with
a timeout warning, it's possible that the acquisition never began because the
trigger level was never reached. The scope will still be waiting to begin
acquisition, but you'll be left without data and with a bad connection.

.. admonition:: Dependencies
   :class: note

   | pyvisa
   | NI-VISA *or* pyvisa-py
"""

# Current Work
# Check out manual, chapter 19.5.2.3
# https://www.rohde-schwarz.com/us/applications/fast-remote-instrument-control-with-hislip-application-note_56280-30881.html
# https://www.google.com/search?channel=tus5&client=firefox-b-1-d&q=pyvisa+hislip
# https://github.com/pyvisa/pyvisa-py/issues/58

# Even though VISAResourceExtensions is not used in this module, the act of 
# importing it alone performs some monkey-patching on the pyvisa module, 
# required by RTO. Don't remove this seemingly unused import!

import time

import pyvisa as visa

from pyrolab import __version__
from pyrolab.drivers.scopes import Scope, VISAResourceExtentions


class RTO(Scope):
    """
    Simple network controller class for R&S RTO oscilloscopes.

    This class is used to control the R&S RTO oscilloscope. These are not local
    devices, nor native PyroLab objects. Therefore, network device 
    autodetection is not supported.
    """
    @staticmethod
    def detect_devices():
        """
        Network device detection not supported.
        
        Becuase R&S oscilloscopes are connected to using the IP address,
        this function does not detect them and instead always returns an empty 
        list.
        """
        device_info = []
        return device_info

    def connect(self, address: str="", hislip: bool=False, timeout: float=1e3) -> bool:
        """
        Connects to and initializes the R&S RTO oscilloscope.
        
        HiSLIP (High-Speed LAN Instrument Protocol) is a TCP/IP-based protocol 
        for remote instrument control of LAN-based test and measurement 
        instruments. It is intended to replace the older VXI-11 protocol.

        .. warning::
           The HiSLIP protocol is not supported when using the pyvisa-py
           backend **on the client machine**. To use it, you must use the NI VISA 
           implementation instead.

        Parameters
        ----------
        address : str
            The IP address of the instrument.
        hislip : bool, optional
            Whether to use the HiSLIP protocol or not (default ``False``).
        timeout : int, optional
            The device response timeout in milliseconds (default 1 ms).
            Pass ``None`` for infinite timeout.
        """
        rm = visa.ResourceManager()
        if hislip:
            self.device = rm.open_resource(f"TCPIP::{address}::hislip0")    
        else:
            self.device = rm.open_resource(f"TCPIP::{address}")
        self.device.timeout = timeout
        self.write_termination = ''
        self.device.ext_clear_status()
        
        self.write('*RST;*CLS')
        self.write('SYST:DISP:UPD ON')
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

    def query(self, message, delay=None):
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

    def wait_for_device(self):
        """
        Waits for the device until last action is complete.

        .. note::
           This function is blocking.
        """
        res = self.device.query('*OPC?')
        time.sleep(0.1)
        return res

    def acquisition_settings(self, sample_rate, duration, force_realtime=False):
        """
        Sets the scope acquisition settings.

        The exact command this executes is:
        `'ACQ:POIN:AUTO RES;:ACQ:SRAT {};:TIM:RANG {}'`

        Parameters
        ----------
        sample_rate : float
            Sample rate of device in Sa/s. Range is 2 to 20e+12 in increments
            of 1.
        duration : float
            Length of acquisition in seconds.
        force_realtime : bool, optional
            Defaults to False.
        """
        short_command = 'ACQ:POIN:AUTO RES;:TIM:RANG {};:ACQ:SRAT {}'.format(duration, sample_rate)
        if force_realtime:
            self.write_block('ACQ:MODE RTIM')
        self.write_block(short_command)

    def set_channel(self, channel: int, state: str="ON", 
                    coupling: str="DCLimit", range: float=0.5, 
                    position: float=0, offset: float=0, invert: str="OFF"):
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

    def __add_trigger(self,
        type,
        source,
        source_num,
        level,
        trigger_num = 1,
        mode = "NORM",
        settings: str = ""):
        short_command = 'TRIG{}:MODE {};SOUR {};TYPE {};LEV{} {};'.format(
        trigger_num, mode, source, type, source_num, level)
        #Add a trigger.
        self.write_block(short_command + settings)

    def edge_trigger(self, channel: int, voltage: float) -> None:
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

    def acquire(self, timeout: int=-1, run: str='single') -> None:
        """
        Asynchronous command that starts acquisition.

        Parameters
        ----------
        timeout : int
            The timeout to use for the given acquisition in milliseconds. The 
            default timeout is used if no timeout is given. The timeout is not
            permanently set; once the acquisition is complete, the original 
            timeout is kept for any other query/write command. For an infinite
            timeout, pass in None. If not specified, default timeout is the 
            default for `acquire()`.
        run : str
            Specifies the type of run. Allowable values are ``continuous`` 
            (starts the continuous acquisition), ``single`` (starts a defined
            number of acquisition cycles as set by 
            :py:func:`acquisition_settings`), or ``stop`` (stops a 
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

        if timeout != -1:
            default_timeout = self.timeout
            self.timeout = timeout
        
        self.write(cmd)

        if timeout != -1:
            self.timeout = default_timeout

    def set_timescale(self, time: float) -> None:
        """
        Sets the horizontal scale--the time per division on the x-axis--for all 
        channel and math waveforms.

        Parameters
        ----------
        time : float
            The time (in seconds) per division. Valid range is from 25e-12 to 
            10000 (RTO) | 5000 (RTE) in increments of 1e-12. (`*RST` value is 
            10e-9).
        """
        self.write(f'TIM:SCAL {str(time)}')

    def set_auto_measurement(self, measurement: int=1, source: str='C1W1', 
                             meastype: str='MAX') -> None:
        """
        Convenience function for setting default measurements. 
        
        Use if you haven't configured any of your own measurements.

        Parameters
        ----------
        measurement : int
            The oscope supports storing up to 8 measurements. Default is 1.
        source : str
            The source to setup the measurement on. See page 1377 of the User
            Manual for valid sources. Common ones are of the format "C<m>W<n>",
            where <m> is the channel and <n> is the waveform (e.g., "C1W1", 
            which is the default).
        meastype : str
            The measurement type to associate with the measurement. See page 
            1381 of the User Manual for valid measurement types. Common ones
            are 'HIGH', 'LOW', 'AMPLitude', 'MAXimum', 'MINimum', 'MEAN'. 
            Default is 'MAX'.
        """
        self.write(f'MEAS{measurement}:SOUR {source}')
        # "MAX" will measure the max value in the current view window (Based on time base)
        self.write(f'MEAS{measurement}:MAIN {meastype}')
        self.write(f'MEAS{measurement} ON')

    def measure(self, measurement: int=1) -> float:
        """
        Takes the result of an automatic measurement as setup using 
        `set_auto_measurement()`.

        Parameters
        ----------
        measurement : int
            The measurement to take. Default is 1.

        Returns
        -------
        float
            The result of the automatic measurement.
        """
        return float(self.query(f'MEAS{measurement}:RES:ACT?'))

    def get_data(self, channel, form="ascii"):
        """
        Retrieves waveform data from the specified channel
        
        Data is retrieved in the specified 
        data type. Note that data like this can be transferred in two ways: 
        in ASCII form (slow, but human readable) and binary (fast, but more 
        difficult to debug).

        Parameters
        ----------
        channel : int
            The channel to retrieve data for.
        form : str, optional
            The data format used for the transmission of waveform data. 
            Allowable values are ``ascii``, ``real``, ``int8``, and ``int16``.
            Default is ``ascii``.

        Notes
        -----
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
        
        # Consider skipping the intermediate "list" step and having pyvisa
        # automatically convert to a numpy array (see
        # https://pyvisa.readthedocs.io/en/latest/introduction/rvalues.html#reading-ascii-values)
        if form == "ascii":
            return self.device.query_ascii_values(cmd)
        elif form == "real":
            return self.device.query_binary_values(cmd)
        else:
            return self.query(cmd)
    
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

    def act_filter(self, channel):
        """
        Activates the lowpass filter for a channel. 

        Parameters
        ----------
        channel : int
            The channel (1-4) on which to activate the filter.
        """
        self.write(f"CHAN{channel}:DIGF:STAT ON")

    def deact_filter(self, channel):
        """
        Deactivates the lowpass filter on a given channel.

        Parameters
        ----------
        channel : int
            The channel (1-4) where the new cutoff frequency is applied.
        """
        self.write(f"CHAN{channel}:DIGF:STAT OFF")
    
    def set_cutoff_freq(self, channel, cutoff_freq):
        """
        Sets the cutoff frequency of one of the two filters: either the filter 
        for channels 1 and 2 or the filter for channels 3 and 4. 
        Cutoff frequencies are set only for either channels 1 and 2 or 
        channels 3 and 4, but you can activate the filter for each channel 
        separately.

        Parameters
        ----------
        channel : int
            Specifies which filter's cutoff frequency will be changed. A value 
            of 1 or 2 will set the cutoff frequency for both channels, and a 
            value of 3 or 4 will do the same for both channels 3 and 4.
        cutoff_freq : int
            The cutoff frequency enabled on the channel. Must be between 100 
            kHz and 1 GHz or 2 GHz (depending on the scope). The scope only supports certain discrete cutoff 
            frequencies. Any other frequency will be rounded to the closest 
            frequency the scope supports.
        """
        if cutoff_freq >= 1e5 and cutoff_freq <= 2e9:
            self.write(f"CHAN{channel}:DIGF:CUT {cutoff_freq}")
        else:
            raise ValueError("Cutoff frequency must be between 1e5 and 2e9 Hz")


class RemoteDisplay:
    def __init__(self, scope: RTO):
        self.scope = scope
        