# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Thorlabs 3-Channel 150V Benchtop Piezo Controller with USB (BPC303)
===================================================================

Driver for the Thorlabs BPC-303 Benchtop Piezo.

.. warning::
   Not all controllers support getting the maximum position. The default maximum
   position is 20 micrometers and when 0 is returned by a device the maximum
   travel for that channel will be defaulted.
"""

import logging
import time
from ctypes import c_char_p, c_int, c_short
from typing import Any, Dict, List

from thorlabs_kinesis import benchtop_piezo as bp

from pyrolab.api import expose, oneway
from pyrolab.drivers.motion.kinesis import KinesisInstrument


log = logging.getLogger(__name__)


MAX_C_SHORT = 32767


@expose
class BPC303(KinesisInstrument):
    """
    A Thorlabs BPC-303 Benchtop Piezo controller.

    Attributes
    ----------
    serialno : str
        The serial number as a Python string.
    poll_period : int
        The polling period in milliseconds.
    max_channels : int
        The number of bays (not necessarily occupied) the device has.
    num_channels : int
        The number of availble channels.
    max_travel : [int]
        Distance in steps of 100nm, range 0 to 65535 (10000 = 1mm) by channel.
    max_voltage : [int]
        Maximum output voltage, 750, 1000 or 1500 (75.0, 100.0, 150.0).
    """

    def connect(
        self,
        serialno: str = "",
        poll_period: int = 200,
        closed_loop: bool = False,
        smoothed: bool = False,
    ) -> None:
        """
        Connects to the device.

        Parameters
        ----------
        serialno : str
            The serial number of the device being connected to as a string.
        poll_period : int, optional
            The polling period (time between data pulls from the device) in ms
            (default 200).
        closed_loop : bool, optional
            Puts controller in open or closed loop mode. Closed loop if True
            (closed loop allows for positional commands instead of voltage
            commands), default False.
        smoothed : bool, optional
            Puts controller in smoothed start/stop mode, default False.

        Raises
        ------
        RuntimeError
            If Kinesis cannot build a device list or no connected devices are found.
        ValueError
            If the serial number is not found in the connected devices.
        """
        if not serialno:
            raise ValueError("No serial number provided.")
        self.serialno = serialno
        self._serialno = c_char_p(bytes(serialno, "utf-8"))  # Store as char array.
        self.poll_period = poll_period

        if bp.TLI_BuildDeviceList() != 0:
            raise RuntimeError("Kinesis error (could not build device list).")
        if bp.TLI_GetDeviceListSize() == 0:
            raise RuntimeError("no connected devices found.")

        # Get list of serial numbers of benchtop-piezo devices connected
        serial_list = c_char_p(bytes("", "utf-8"))
        bp.TLI_GetDeviceListByTypeExt(serial_list, 250, 71)
        serial_nos = serial_list.value.decode("utf-8").split(",")
        if self.serialno not in serial_nos:
            raise ValueError("serial number not found in connected devices.")

        # Open the device for communication
        bp.PBC_Open(self._serialno)

        # Generate valid channels
        self.max_channels = bp.PBC_MaxChannelCount(self._serialno)
        self.num_channels = bp.PBC_GetNumChannels(self._serialno)
        self.channels = []
        self._channels = []
        for channel in range(1, self.num_channels + 1):
            if bp.PBC_IsChannelValid(self._serialno, c_short(channel)):
                self.channels.append(channel)
                self._channels.append(c_short(channel))

        # Ask for the max travel of each axis. If it returns zero, this
        # function is not supported by the module.
        self.max_travel = []
        for channel in self._channels:
            if bp.PBC_RequestMaximumTravel(self._serialno, channel):
                time.sleep(1.2 * self.poll_period / 1000)
                self.max_travel.append(
                    int(bp.PBC_GetMaximumTravel(self._serialno, channel))
                )
            else:
                raise RuntimeError("maximum travel request to device failed.")

        self.max_voltage = []
        for channel in self._channels:
            if bp.PBC_RequestMaxOutputVoltage(self._serialno, channel):
                time.sleep(1.2 * self.poll_period / 1000)
                self.max_voltage.append(
                    bp.PBC_GetMaxOutputVoltage(self._serialno, channel)
                )
            else:
                raise RuntimeError("maximum voltage request to device failed.")

        self.enable_channel()
        self.set_position_control_mode(closed_loop=closed_loop, smoothed=smoothed)
        self._start_polling()

    def _start_polling(self) -> None:
        """
        Starts polling data from device (device self updates position and
        status).
        """
        for channel in self._channels:
            bp.PBC_StartPolling(self._serialno, channel, c_int(self.poll_period))

        # Clear prior messages
        bp.PBC_ClearMessageQueue(self._serialno)
        time.sleep(1)

    @staticmethod
    def detect_devices() -> List[Dict[str, Any]]:
        """
        Detect all KCube DC Servo devices connected to the computer.

        .. warning::

            Not currently implemented.
        """
        log.debug("Entering `detect_devices()`")
        return []

    def close(self) -> None:
        """
        Disconnects and closes the device, releasing the resource.
        """
        self._stop_polling()
        bp.PBC_Disconnect(self._serialno)
        bp.PBC_Close(self._serialno)

    def _stop_polling(self) -> None:
        """
        Stop polling data from the device.
        """
        for channel in self._channels:
            bp.PBC_StopPolling(self._serialno, channel)

    def identify(self, channel: int) -> None:
        """
        Asks some channel of a device to identify itself.

        Parameters
        ----------
        channel : int
            The channel to be identified (1-n).
        """
        channel = self._verify_channel(channel)
        bp.PBC_Identify(self._serialno, channel)

    def check_connection(self) -> bool:
        """
        Checks connection of the device.

        Returns
        -------
        connected : bool
            True if the USB is listed by the ftdi controller.
        """
        return bp.PBC_CheckConnection(self._serialno)

    def enable_channel(self, channel: int = None) -> None:
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
        else:
            channel = self._verify_channel(channel)
            bp.PBC_EnableChannel(self._serialno, channel)

    def disable_channel(self, channel: int = None) -> None:
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
            The channel to to set the control mode for (1-n). Gets for all if
            ``None``.

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
        return bp.PBC_GetPositionControlMode(self._serialno, channel)

    def set_position_control_mode(
        self, channel: int = None, closed_loop: bool = False, smoothed: bool = False
    ) -> None:
        """
        Sets position control mode of the device.

        Parameters
        ----------
        channel : bool, optional
            The channel to to set the control mode for (1-n). Sets for all if
            ``None``.
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
            channel = self._verify_channel(channel)
            bp.PBC_SetPositionControlMode(self._serialno, channel, c_short(mode))

    def position(self, channel: int, percent: int = None) -> int:
        """
        Sets the position of the requested channel when in closed loop mode.
        If no position is specified, simply returns the current position.

        Parameters
        ----------
        channel : int
            The channel to get or set the position for (1-n).
        percent : int, optional
            The position as a percentage of maximum travel, range 0 to 32767,
            equivalent to 0 to 100%. If not specified (None), current position
            is returned.

        Returns
        -------
        pos : int
            The position as a percentage of maximum travel, range -32767 to
            32767, equivalent to -100 to 100%. The result is undefined if not
            in closed loop mode.
        """
        channel = self._verify_channel(channel)

        if percent is not None:
            percent = self._saturate(percent, 0, MAX_C_SHORT)
            bp.PBC_SetPosition(self._serialno, channel, c_short(percent))
        else:
            return bp.PBC_GetPosition(self._serialno, channel)

    def voltage(self, channel: int, percent: int = None) -> int:
        """
        Sets the output voltage of the requested channel. If no voltage is
        specified, simply returns the current voltage.

        Parameters
        ----------
        channel : int
            The channel to get or set the position for (1-n).
        percent : int, optional
            The voltage as a percentage of max_voltage, range -32767 to
            32767 equivalent to -100% to 100%. If not specified, current
            voltage is returned.

        Returns
        -------
        percent : int
            The current voltage of the selected channel as a percentage of
            maximum output voltage, range -32767 to 32767 equivalent to
            -100% to 100%.

        Raises
        ------
        RuntimeError
            If the request to the Kinesis DLL fails.
        """
        channel = self._verify_channel(channel)

        if percent is not None:
            percent = self._saturate(percent, -MAX_C_SHORT, MAX_C_SHORT)
            bp.PBC_SetOutputVoltage(self._serialno, channel, c_short(percent))
        else:
            return bp.PBC_GetOutputVoltage(self._serialno, channel)

    # def wait_for_message(self):
    #     """
    #     Gets the next item from the device's message queue. Can potentially be
    #     used as a blocking function.
    #     """
    #     pass

    @oneway
    def zero(self, channel: int = None, block: bool = True) -> None:
        """
        Zeroes a channel (or all). Automatically sets closed loop mode.

        Parameters
        ----------
        channel : int, optional
            The channel to zero (1-n). If not specified, zeroes all channels.
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

    def _verify_channel(self, channel: int) -> c_short:
        """
        Verifies that a channel is valid for the connected device.

        Parameters
        ----------
        channel : int
            The channel number to verify (1-n).

        Returns
        -------
        channel : c_short
            The channel as a c_short for use in Kinesis DLL function calls.

        Raises
        ------
        TypeError
            If channel is not an integer.
        ValueError
            If the requested channel is invalid.
        """
        if type(channel) is not int:
            raise TypeError("'channel' must be an integer.")
        if channel not in [chan.value for chan in self._channels]:
            raise ValueError("requested channel '{}' is invalid".format(channel))
        else:
            return c_short(channel)

    def _saturate(self, value: float, minimum: float, maximum: float) -> float:
        """
        Saturates a value at a given minimum and maximum.

        Parameters
        ----------
        value : float
            The value to saturate.
        minimum : float
            The minimum allowable value.
        maximum : float
            The maximum allowable value.

        Returns
        -------
        value : float
            A value guaranteed to be between ``minimimum`` and ``maximum``.
        """
        if value > maximum:
            value = maximum
        if value < minimum:
            value = minimum
        return value
