# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Thorlabs 3-Channel 150V Benchtop Piezo Controller with USB (BPC303)
-------------------------------------------------------------------
Driver for the Thorlabs BPC-303 Benchtop Piezo.

Author: David Hill (https://github.com/hillda3141)  
Repo: https://github.com/BYUCamachoLab/pyrolab

Warning
-------
Not all controllers support getting the maximum position. The default maximum
position is 20 micrometers and when 0 is returned by a device the maximum
travel for that channel will be defaulted.
"""

import time
from typing import Type
from thorlabs_kinesis import benchtop_piezo as bp

from ctypes import (
    c_short,
    c_char_p,
    c_void_p,
    byref,
    c_int,
    create_string_buffer,
)
from ctypes.wintypes import (
    DWORD,
    WORD,
)


MAX_C_SHORT = 32767


class ChannelInformation:
    def __init__(self):
        pass


class BPC303:
    """ 
    A Thorlabs BPC-303 Benchtop Piezo controller.

    Device connection is attempted upon instantiation of this class.

    Parameters
    ----------
    serialno : str
        The serial number of the device being connected to as a string.
    poll_period : int, optional
        The polling period (time between data pulls from the device) in ms 
        (default 200).
    closed_loop : bool, optional
    smoothed : bool, optional

    Attributes
    ----------
    serialno : str
        The serial number as a Python string.
    poll_period : int
        The polling period in milliseconds.
    MAX_C_SHORT : [int, *]
        Distance in steps of 100nm, range 0 to 65535 (10000 = 1mm) by channel.
    """
    def __init__(self, serialno: str, poll_period: int=200, closed_loop: bool=False, smoothed: bool=False):
        self.serialno = serialno
        # Store serialno as c-type char array.
        self._serialno = c_char_p(bytes(serialno, "utf-8"))
        self.poll_period = poll_period

        if bp.TLI_BuildDeviceList() != 0:   #if there are errors building devices
            return 0
        if bp.TLI_GetDeviceListSize() == 0: #if there are no devices
            return 0
        if not self.check_serial():    #get the serial number of the BP303
            return 0
        bp.PBC_Open(self._serialno)       # open the device for communication

        self.num_channels = 3 # FIXME
        self.channels = []
        self._channels = []

        # Generate valid channels
        for channel in range(1, self.num_channels):
            if bp.PBC_IsChannelValid(self._serialno, c_short(channel)):
                self.channels.append(channel)
                self._channels.append(c_short(channel))

        self.enable_channel()

        self.MAX_C_SHORT = []
        for channel in self._channels:
            # Ask for the max travel of each axis. If it returns zero, this 
            # function is not supported by the module
            self.MAX_C_SHORT.append(int(bp.PBC_GetMaxTravel(self._serialno, channel)))

        # Do something with closed_loop and smoothed.
        self.set_position_control_mode(closed_loop, smoothed)
        self._start_polling() #start polling data

    def _start_polling(self):
        """
        Starts polling data from device (device self updates position and 
        status).
        """
        for channel in self._channels:
            bp.PBC_StartPolling(self._serialno, channel, c_int(self.poll_period))
        
        # Clear prior messages
        bp.PBC_ClearMessageQueue(self._serialno)
        time.sleep(1)

    def close(self):
        """
        Disconnects and closes the device.
        """
        self._stop_polling()
        bp.PBC_Disconnect(self._serialno)
        bp.PBC_Close(self._serialno)

    def _stop_polling(self):
        """
        Stop polling data from the device.
        """
        for channel in self._channels:
            bp.PBC_StopPolling(self._serialno, channel)

    def identify(self, channel: int):
        """
        Asks some channel of a device to identify itself.

        Parameters
        ----------
        channel : int
            The channel to be identified.
        """
        self._verify_channel(channel)
        bp.PBC_Identify(c_short(channel))

    # def check_connection(self):
    def check_serial(self):
        """
        checks to ensure there is a benchtop piezo device connected with that serial number
        """
        serialList = c_char_p(bytes("","utf-8"))
        bp.TLI_GetDeviceListByTypeExt(serialList, 250, 71)  # get list of serial numbers of benchtop-piezo devices connected
        for i in range(0,40,10):
            tempNum = (serialList.value[i:i+8]).decode("utf-8")
            if tempNum=="":
                return False
            if int(tempNum)==int((self.serialno.value[0:8]).decode("utf-8")):
                return True

    def enable_channel(self, channel: int=None):
        """
        Enables communication for a specific channel (or all).

        Parameters
        ----------
        channel : int, optional
            The channel to be enabled (1-n). If not specified, enables all
            channels.
        """
        if channel is None:
            for chan in self._channels:
                bp.PBC_EnableChannel(self._serialno, chan)
        elif type(channel) is int:
            bp.PBC_EnableChannel(self._serialno, c_short(channel))

    def disable_channel(self, channel: int=None):
        """
        Disables communication for a specific channel (or all).

        Parameters
        ----------
        channel : int, optional
            The channel to be disabled (1-n). If not specified, disables all
            channels.
        """
        if channel is None:
            for chan in self._channels:
                bp.PBC_DisableChannel(self._serialno, chan)
        else:
            channel = self._verify_channel(channel)
            bp.PBC_DisableChannel(self._serialno, channel)

    def get_position_control_mode(self, channel: int) -> int:
        """
        Gets the position control mode of the device.

        Parameters
        ----------
        channel : bool, optional
            The channel to to set the control mode for. Sets for all if None.

        Returns
        -------
        mode : int
            The position control mode of the device.
            1 - Open Loop
            2 - Closed Loop
            3 - Open Loop smoothed
            4 - Closed Loop smoothed
        """
        channel = self._verify_channel(channel)
        mode = bp.PBC_GetPositionControlMode(self._serialno, channel)
        return mode.value

    def set_position_control_mode(self, channel: int=None, closed_loop: bool=False, smoothed: bool=False):
        """
        Sets position control mode of the device.

        Parameters
        ----------
        channel : bool, optional
            The channel to to set the control mode for. Sets for all if None.
        closed_loop : bool, optional
            Sets the position control mode; closed loop if True (default False 
            means open loop). 
        smoothed : bool, optional
            Sets the control smoothing mode; smoothed if True (default False).
        """
        mode = 1
        if closed_loop:
            mode += 1
        if smoothed:
            mode += 2
        
        if channel is None:
            for chan in self._channels:
                bp.PBC_SetPositionControlMode(self._serialno, chan, c_short(mode))
        else:
            channel = self._verify_channel
            bp.PBC_SetPositionControlMode(self._serialno, channel, c_short(mode))

    def position(self, channel: int, percent: float=None) -> float:
        """
        Sets the position of the requested channel when in closed loop mode. 
        If no position is specified, simply returns the current position.

        Parameters
        ----------
        channel : int
            The channel to get or set the position for.
        position : float, optional
            The position to go to as a percentage of max travel (0 to 100%).
            If not specified, current position is returned.

        Returns
        -------
        position : float
            The current position of the selected channel as a percentage of
            maximum travel, range -100 to 100%.
        """
        channel = self._verify_channel(channel)

        if percent is not None:
            norm_position = c_short(round(percent/100 * MAX_C_SHORT))
            bp.PBC_SetPosition(self._serialno, channel, norm_position)
        else:
            pos = bp.PBC_GetPosition(self._serialno, channel)
            percent = pos.value / MAX_C_SHORT
            return percent

    def output_voltage(self, channel, percent) -> float:
        """
        Sets the output voltage of the requested channel. If no voltage is
        specified, simply returns the current voltage.

        Parameters
        ----------
        channel : int
            The channel to get or set the position for.
        percent : float
            The position to go to as a percentage of max travel (-100 to 100%).
            If not specified, current position is returned.

        Returns
        -------
        position : float
            The current voltage of the selected channel as a percentage of
            maximum output voltage, range -100 to 100%.
        """
        channel = self._verify_channel(channel)

        if percent is not None:
            norm_voltage = c_short(round(percent/100 * MAX_C_SHORT))
            bp.PBC_SetOutputVoltage(self._serialno, channel, norm_voltage)
        else:
            if bp.PBC_RequestOutputVoltage(self._serialno, channel):
                voltage = bp.PBC_GetOutputVoltage(self._serialno, channel)
                percent = voltage.value / MAX_C_SHORT
                return percent
            else:
                raise RuntimeError("output voltage request failed.")

    def wait_for_message(self):
        pass

    def zero(self, channel: int=None, block: bool=True):
        """
        Zeroes a channel (or all). Automatically sets closed loop mode.
        
        Parameters
        ----------
        channel : int, optional
            The channel to zero. If not specified, zeroes all channels.
        block : bool, optional
            If True, this function is blocking.
        """
        if channel is None:
            for chan in self._channels:
                bp.PBC_SetZero(self._serialno, chan)
        else:
            channel = self._verify_channel(channel)
            bp.PBC_SetZero(self._serialno, channel)
        
        if block:
            time.sleep(25)

    def _verify_channel(self, channel: int):
        """
        Verifies that a channel is valid for the connected device.
        """
        if type(channel) is not int:
            raise TypeError("'channel' must be an integer.")
        if channel not in [chan.value for chan in self._channels]:
            raise ValueError("Requested channel '{}' is invalid".format(channel))
        else:
            return c_short(channel)
