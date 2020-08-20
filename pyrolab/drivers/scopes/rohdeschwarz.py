# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Rohde & Schwarz Digital Oscilloscopes
------

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
"""
import pyvisa as visa

from pyrolab.drivers.scopes import Scope, VISAResourceExtentions

class RTO(Scope):
    """
    Simple network controller class for R&S RTO oscilloscopes.


    
    """
    def __init__(self, address):
        rm = visa.ResourceManager()
        self.device = rm.open_resource("TCPIP::{}::INSTR".format(address))
        self.device.write_termination = ''
        self.device.ext_clear_status()
        
        print("Connected: {}".format(self.device.query('*IDN?')))
        self.device.write('*RST;*CLS')
        self.device.write('SYST:DISP:UPD ON')
        self.device.ext_error_checking()

    def query(self, message, delay=None):
        """
        A combination of ``write(message)`` and ``read()``.

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
        self.device.write(message)
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

    def add_channel(self, channel, range, position=0, offset=0, coupling="DCL"):
        """
        Adds a channel.

        Parameters
        ----------
        channel : int
            The channel number to be added.
        range : float
        position : float, optional
        offset : float, optional
        coupling : str

        """
        short_command = 'CHAN{}:RANG {};POS {};OFFS {};COUP {};STAT ON'.format(
            channel, range, position, offset, coupling
        )
        self.write_block(short_command)

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

    def start_acquisition(self, timeout, type='SING'):
        self.device.timeout = timeout*1000 #Translate seconds to ms.
        self.device.write(type)

    def get_data_ascii(self, channel):
        dataQuery = 'FORM ASC;:CHAN{}:DATA?'.format(channel)
        waveform = self.device.query_ascii_values(dataQuery)
        return waveform

    def get_data_binary(self, channel):
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