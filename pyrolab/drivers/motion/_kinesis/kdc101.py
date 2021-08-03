# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
KDC101
------

Submodule that implements the basic functionality of the KCube DC Servo.

Kinesis controllers are only available on Windows machines. Proxies from
other operating systems can however call Pyro services freely.

ThorLabs Kinesis should be installed, see ThorLabs' website to download.

.. note::
   If you are using the remote functionalities of PyroLab, you may see the
   error ``RuntimeError: FT_DeviceNotFound`` when calling functions on objects
   inheriting from KDC101. This sometimes occus when you forget to call
   ``autoconnect()`` before trying to use the device.
"""

import time
import logging
from ctypes import (
    c_bool,
    c_short,
    c_char_p,
    c_void_p,
    byref,
    c_uint,
    c_int,
    c_long,
    c_float,
    c_double,
    create_string_buffer,
    cast,
)
from ctypes.wintypes import DWORD, WORD
from typing import Any, Dict, List

from Pyro5.server import oneway
from thorlabs_kinesis import kcube_dcservo as kcdc
from thorlabs_kinesis._utils import c_word, c_dword

from pyrolab.drivers.motion._kinesis import KinesisInstrument, ERROR_CODES
from pyrolab.api import expose
from pyrolab.drivers.motion._kinesis.exceptions import (
    KinesisCommunicationError,
    KinesisDLLError,
    KinesisMotorError,
)

log = logging.getLogger("pyrolab.drivers.motion._kinesis.kdc101")


KCube_DC_Servo_Device_ID = 27


def check_error(status):
    if status != 0:
        if status > 0 and status <= 21:
            raise KinesisCommunicationError(ERROR_CODES[status], errcode=status)
        elif (status >= 32 and status <= 36) or (status >= 41 and status <= 43):
            raise KinesisDLLError(ERROR_CODES[status], errcode=status)
        elif( status >= 37 and status <= 39) or (status >= 44 and status <= 47):
            raise KinesisMotorError(ERROR_CODES[status], errcode=status)
        raise RuntimeError(ERROR_CODES[status])


log.info("Building ThorLabs device list (requires ThorLabs Kinesis DLL)")
try:
    kcdc.TLI_BuildDeviceList()
except:
    log.warn("Building ThorLabs device list failed; unable to connect to any instruments")


class HomingMixin:
    def home(self, block=True):
        log.debug(f"Homing KDC101 device '{self.serialno}'")
        status = kcdc.CC_Home(self._serialno)
        check_error(status)
        if block:
            self.wait_for_completion()

# TODO: Are requests necessary when polling is active?
# TODO: One potential way of implementing non-blocking functions is by always 
# clearing all message queues before starting any of the requests. Then, 
# message from previous non-blocking calls don't get consumed by new requestors.


@expose
class KDC101(KinesisInstrument):
    """
    A KCube DC Servo motor. 

    Parameters
    ----------
    serialno : int
        The serial number of the device to connect to.
    polling : int, optional
        The polling rate in milliseconds (default 200).
    home : bool
        Whether to automatically home the device upon connection
        (default ``False``).

    Attributes
    ----------
    serialno : str
        The serial number as a string.
    homed : bool
        True if the devicd has been homed since being opened
    backlash : float
        The backlash setting (used to control hysteresis) in real units
    homing_velocity : float
        The homing velocity in real units. It is always a positive number.
    jog_mode : str
        The jog mode can be either ``stepped`` (fixed distance, single step) or 
        ``continuous`` (move continuously until stopped).
    jog_step_size : float
        The distance to move in real units when jogging.
    stop_mode : str
        The stop mode, either ``immediate`` (stops immediately) or ``profiled`` 
        (stops, using the current velocity profile).
    max_pos : float
        The stage axis maximum position limit in real units.
    min_pos : float
        The stage axis minimum position limit in real units.
    soft_limits_mode : str
        The software limits mode 
        ``disallow``: Disable any move outside of the current travel range of 
        the stage.
        ``partial``: Truncate moves to within the current travel range of the 
        stage.
        ``all``: Allow all moves, regardless of whether they are within the 
        current travel range of the stage. 
    move_velocity : float
        The move velocity in real units. It is always a positive number.
    move_acceleration: float
        The move acceleration in real units. It is always a positive number.
    jog_velocity : float
        The jog velocity in real units. It is always a positive number.
    jog_acceleration : float
        The jog acceleration in real units. It is always a positive number.
    """
    CONDITIONS = ["homed", "moved", "stopped", "limit_updated"]

    def __init__(self) -> None:
        log.debug("KDC101 created")
        super().__init__()

    def connect(self, serialno: str = "", polling=200, home=False):
        log.debug("Entering `connect()`")
        # TODO: Build an exception for this.
        if not serialno:
            raise ValueError("No serial number provided.")
        # self.home = home # This isn't used anywhere else...
        self.serialno = serialno
        self._serialno = c_char_p(bytes(str(serialno), "utf-8"))
        check_error(kcdc.CC_Open(self._serialno))

        # Get and store device info
        self._device_info = kcdc.TLI_DeviceInfo()
        kcdc.TLI_GetDeviceInfo(self._serialno, byref(self._device_info))

        # IMPORTANT: Initialize and persist the correct settings to the device
        # using the kinesis software before loading the setting here as it could
        # load settings that are vital to converting between du and real units
        kcdc.CC_LoadSettings(self._serialno)
        kcdc.CC_SetLimitsSoftwareApproachPolicy(self._serialno, c_short(1))

        # Open communication with the device
        kcdc.CC_StartPolling(self._serialno, c_int(polling))

        # Sleep while device initialization occurs
        time.sleep(3)

        # Clear the message queue
        kcdc.CC_ClearMessageQueue(self._serialno)

        if home:
            if not kcdc.CC_CanHome(self._serialno):
                self.homed = False
                raise RuntimeError("Device '{}' is not homeable.")
            else:
                self.go_home()
        else:
            self.homed = False

        log.debug("Exiting `connect()`")

    @staticmethod
    def detect_devices() -> List[Dict[str, Any]]:
        log.debug("Entering `detect_devices()`")
        return []

    def _du_to_real_value(self, du, unit_type):
        """
        Converts a device unit to a real world unit. 
        The motor stage parameters define the stage motion in terms of Real 
        World Units (mm or degrees). The real world unit is defined from:

            stepsPerRev * gearBoxRatio / pitch.

        Use CC_GetMotorParamsExt() if curious about the motor stage parameters.

        TLI_BuildDeviceList() and CC_loadSettings() must have be executed before
        using the conversion functions. The correct setting must be persisted on 
        the device in kinesis before using CC_loadSettings() to ensure the 
        device has the correct motor stage parameters.

        Parameters
        ----------
        du : int
            The value in device units.
        unit_type : int
            The type of unit being converted; ``0`` for distance, ``1`` for 
            velocity, or ``2`` for acceleration.
        """
        log.debug("Entering `_du_to_real_value()`")
        real_unit = c_double()
        status = kcdc.CC_GetRealValueFromDeviceUnit(
            self._serialno,
            c_int(du),
            byref(real_unit),
            c_int(unit_type))
        check_error(status)
        return real_unit.value

    def _real_value_to_du(self, real, unit_type):
        """
        Converts a device unit to a real world unit. 

        Parameters
        ----------
        real : float
            The value to be converted to device units.
        unit_type : int
            The type of unit being converted; ``0`` for distance, ``1`` for 
            velocity, or ``2`` for acceleration.
        """
        log.debug("Entering `_real_value_to_du()`")
        device_unit = c_int()
        status = kcdc.CC_GetDeviceUnitFromRealValue(
            self._serialno,
            c_double(real),
            byref(device_unit),
            c_int(unit_type))
        check_error(status)
        return device_unit.value

    @property
    def backlash(self):
        """
        Get the backlash distance setting (used to control hysteresis). 
        """
        log.debug("Entering `backlash()`")
        backlash = kcdc.CC_GetBacklash(self._serialno)

        return self._du_to_real_value(backlash, 0)

    @backlash.setter
    def backlash(self, val):
        """
        FIXME: backlash returns in real values, but this takes in device units?
        """
        status = kcdc.CC_SetBacklash(self._serialno, c_long(val))
        check_error(status)

    @property
    def homing_velocity(self):
        """
        Gets the homing velocity.
        """
        velocity = kcdc.CC_GetHomingVelocity(self._serialno)
        return velocity

    @homing_velocity.setter
    def homing_velocity(self, velocity):
        """
        Sets the homing velocity.
        """
        status = kcdc.CC_SetHomingVelocity(self._serialno, c_uint(velocity))
        check_error(status)

    @property
    def jog_mode(self):
        log.debug("Entering `jog_mode()`")
        jog_mode = kcdc.MOT_JogModes()
        stop_mode = kcdc.MOT_StopModes()
        status = kcdc.CC_GetJogMode(
            self._serialno,
            byref(jog_mode),
            byref(stop_mode))
        check_error(status)
        if jog_mode.value == kcdc.MOT_Continuous.value:
            return "continuous"
        elif jog_mode.value == kcdc.MOT_SingleStep.value:
            return "stepped"
        else:
            raise RuntimeError("Unexpected value received from Kinesis")

    @jog_mode.setter
    def jog_mode(self, jog_mode):
        log.debug("Setting `jog_mode()`")
        c_jog_mode = kcdc.MOT_JogModeUndefined
        c_stop_mode = kcdc.MOT_StopModeUndefined
        stop_mode = self.stop_mode

        if jog_mode == "continuous":
            c_jog_mode = kcdc.MOT_Continuous
        elif jog_mode == "stepped":
            c_jog_mode = kcdc.MOT_SingleStep
        if stop_mode == "immediate":
            c_stop_mode = kcdc.MOT_Immediate
        elif stop_mode == "profiled":
            c_stop_mode = kcdc.MOT_Profiled

        kcdc.CC_SetJogMode(self._serialno, c_jog_mode, c_stop_mode)

    @property
    def jog_step_size(self):
        log.debug("Entering `jog_step_size(self)`")
        return self._du_to_real_value(kcdc.CC_GetJogStepSize(self._serialno), 0)

    @jog_step_size.setter
    def jog_step_size(self, step_size):
        c_step_size = self._real_value_to_du(step_size, 0)
        status = kcdc.CC_SetJogStepSize(self._serialno, c_uint(c_step_size))
        check_error(status)

    @property
    def stop_mode(self):
        jog_mode = kcdc.MOT_JogModes()
        stop_mode = kcdc.MOT_StopModes()
        status = kcdc.CC_GetJogMode(
            self._serialno,
            byref(jog_mode),
            byref(stop_mode))
        check_error(status)
        if stop_mode.value == kcdc.MOT_Immediate:
            return "immediate"
        elif jog_mode.value == kcdc.MOT_Profiled.value:
            return "profiled"
        else:
            raise RuntimeError("Unexpected value received from Kinesis")

    @stop_mode.setter
    def stop_mode(self, stop_mode):
        c_jog_mode = kcdc.MOT_JogModeUndefined()
        c_stop_mode = kcdc.MOT_StopModeUndefined()
        jog_mode = self.jog_mode

        if jog_mode == "continuous":
            c_jog_mode = kcdc.MOT_Continuous
        elif jog_mode == "stepped":
            c_jog_mode = kcdc.MOT_SingleStep
        if stop_mode == "immediate":
            c_stop_mode = kcdc.MOT_Immediate
        elif stop_mode == "profiled":
            c_stop_mode = kcdc.MOT_Profiled

        kcdc.CC_SetJogMode(self._serialno, c_jog_mode, c_stop_mode)

    @property
    def max_pos(self):
        max_pos = c_int()
        max_pos = kcdc.CC_GetStageAxisMaxPos(self._serialno)
        return self._du_to_real_value(max_pos, 0)

    @max_pos.setter
    def max_pos(self, max):
        min = self.min_pos
        status = kcdc.CC_SetStageAxisLimits(
            self._serialno,
            c_int(self._real_value_to_du(min, 0)),
            c_int(self._real_value_to_du(max, 0)))
        check_error(status)
        self.wait_for_completion("limit_updated")

    @property
    def min_pos(self):
        min_pos = c_int()
        min_pos = kcdc.CC_GetStageAxisMinPos(self._serialno)
        return self._du_to_real_value(min_pos, 0)

    @min_pos.setter
    def min_pos(self, min):
        max = self.max_pos
        status = kcdc.CC_SetStageAxisLimits(
            self._serialno,
            c_int(self._real_value_to_du(min, 0)),
            c_int(self._real_value_to_du(max, 0)))
        check_error(status)
        self.wait_for_completion("limit_updated")

    @property
    def soft_limits_mode(self):
        mode = kcdc.CC_GetSoftLimitMode(self._serialno)
        mode = c_short(mode)
        if mode.value == kcdc.DisallowIllegalMoves.value:
            return "disallow"
        elif mode.value == kcdc.AllowPartialMoves.value:
            return "partial"
        elif mode.value == kcdc.AllowAllMoves.value:
            return "all"
        else:
            raise RuntimeError("Unexpected value received from Kinesis")

    @soft_limits_mode.setter
    def soft_limits_mode(self, mode):
        c_mode = kcdc.MOT_LimitsSoftwareApproachPolicy
        if mode == "disallow":
            c_mode = kcdc.DisallowIllegalMoves
        elif mode == "partial":
            c_mode = kcdc.AllowPartialMoves
        elif mode == "all":
            c_mode = kcdc.AllowAllMoves

        kcdc.CC_SetLimitsSoftwareApproachPolicy(self._serialno, c_mode)

    @property
    def move_velocity(self):
        accel = c_int()
        vel = c_int()
        status = kcdc.CC_GetVelParams(self._serialno, byref(accel), byref(vel))
        check_error(status)
        return self._du_to_real_value(vel.value, 1)

    @move_velocity.setter
    def move_velocity(self, velocity):
        status = kcdc.CC_SetVelParams(
            self._serialno,
            c_int(self._real_value_to_du(self.move_acceleration, 2)),
            c_int(self._real_value_to_du(velocity, 1)))
        check_error(status)

    @property
    def move_acceleration(self):
        accel = c_int()
        vel = c_int()
        status = kcdc.CC_GetVelParams(self._serialno, byref(accel), byref(vel))
        check_error(status)
        return self._du_to_real_value(accel.value, 2)

    @move_acceleration.setter
    def move_acceleration(self, acceleration):
        status = kcdc.CC_SetVelParams(
            self._serialno,
            c_int(self._real_value_to_du(acceleration, 2)),
            c_int(self.move_velocity))
        check_error(status)

    @property
    def jog_velocity(self):
        accel = c_int()
        vel = c_int()
        status = kcdc.CC_GetJogVelParams(
            self._serialno,
            byref(accel),
            byref(vel))
        check_error(status)
        return self._du_to_real_value(vel.value, 1)

    @jog_velocity.setter
    def jog_velocity(self, velocity):
        status = kcdc.CC_SetJogVelParams(
            self._serialno,
            c_int(self._real_value_to_du(self.move_acceleration, 2)),
            c_int(self._real_value_to_du(velocity, 1)))
        check_error(status)

    @property
    def jog_acceleration(self):
        accel = c_int()
        vel = c_int()
        status = kcdc.CC_GetJogVelParams(
            self._serialno,
            byref(accel),
            byref(vel))
        check_error(status)
        return self._du_to_real_value(accel.value, 2)

    @jog_acceleration.setter
    def jog_acceleration(self, acceleration):
        status = kcdc.CC_SetJogVelParams(
            self._serialno,
            c_int(self._real_value_to_du(acceleration, 2)),
            c_int(self.move_velocity))
        check_error(status)

    def get_position(self):
        """
        Gets the current position of the stage in real units.

        Returns
        -------
        pos : float
            The current position of the stage in real units.
        """
        log.debug("Entering `get_position()`")
        current_pos_du = kcdc.CC_GetPosition(self._serialno)
        return self._du_to_real_value(current_pos_du, 0)

    def get_status_bits(self) -> int:
        """
        Returns the status bits of the motor. See the ThorLabs Kinesis 
        documentation for bitmasks to access various status values.

        Returns
        -------
        status_bits : int
            The status bits of the motor.
        """
        return kcdc.CC_GetStatusBits(self._serialno)

    def is_moving(self) -> bool:
        """
        Returns whether the motor is moving (clockwise or counterclockwise).
        Does not return True if the motor is moving by jogging or if movement
        is due to homing.

        Returns
        -------
        is_moving : bool
            Whether the motor is moving.
        """
        bits = self.get_status_bits()
        if (bits & 0x10) or (bits & 0x20):
            return True
        else:
            return False

    def wait_for_completion(self, id="homed", MAX_WAIT_TIME=5):
        """
        A blocking function to ensure a task has been finished.

        Used to for the following functions: homing, moving, stopping, or 
        updating limits. The id parameter must be specificed for the correct 
        operation ("homed", "moved", "stopped", or "limit_updated").

        If the task is not finished after MAX_WAIT_TIME, a RuntimeError is
        raised. If the id is "homed", MAX_WAIT_TIME is ignored.

        Parameters
        ----------
        id : str, optional
            must be either "homed", "moved", "stopped", or "limit_updated"
            (default is "homed").
        MAX_WAIT_TIME : int, optional
            The maximum time to wait for the task to complete. Defaults to 5 
            seconds. Ignored if id is "homed".

        Raises
        ------
        RuntimeError
            If the task is not finished after MAX_WAIT_TIME seconds.
        """
        log.debug("Entering `wait_for_completion()`")
        # TODO: "id" is a reserved keyword in Python. Change this!
        message_type = c_word()
        message_id = c_word()
        message_data = c_dword()

        cond = self.CONDITIONS.index(id)
        log.debug(f"Condition index: {cond} - {id} ")

        # If the motor is already stopped, perhaps because it reached a limit,
        # it will wait forever for a message! So just return.
        if id == "stopped":
            if not self.is_moving():
                log.debug("Exiting `wait_for_completion()`")
                return
        elif id == "homed":
            # Homing might take a while.
            MAX_WAIT_TIME = 0

        while kcdc.CC_MessageQueueSize(self._serialno) <= 0:
            log.debug(f"Waiting for message (KDC101 '{self.serialno}')")
            time.sleep(0.2)
        kcdc.CC_WaitForMessage(
            self._serialno,
            byref(message_type),
            byref(message_id),
            byref(message_data)
        )

        log.debug("Entering wait loop")
        start = time.time()
        while int(message_type.value) != 2 or int(message_id.value) != cond:
            end = time.time()
            if (end - start > MAX_WAIT_TIME) and (MAX_WAIT_TIME != 0):
                log.debug(f"Message queue size: {kcdc.CC_MessageQueueSize(self._serialno)}")
                raise RuntimeError(
                    f"Waited for {MAX_WAIT_TIME} seconds for {id} to complete. "
                    f"Message type: {message_type.value}, Message ID: {message_id.value}")

            if kcdc.CC_MessageQueueSize(self._serialno) <= 0:
                log.debug(f"Waiting for message (KDC101 '{self.serialno}')")
                time.sleep(0.2)
                continue
            kcdc.CC_WaitForMessage(
                self._serialno,
                byref(message_type),
                byref(message_id),
                byref(message_data))
        log.debug("Exiting `wait_for_completion()`")

    def identify(self):
        """
        Sends a command to the device to make it identify iteself.
        """
        log.debug("Entering `identify()`")
        kcdc.CC_Identify(self._serialno)

    # @oneway
    def go_home(self):
        """
        Takes the device home and sets self.homed to true

        go_home() will always ignore the software limits from soft_limits_mode 
        and min_pos and max_pos.

        FIXME: This function shouldn't exist; it's provided by HomingMixin
        """
        log.debug(f"Homing KDC101 device '{self.serialno}'")
        status = kcdc.CC_Home(self._serialno)
        check_error(status)
        self.homed = True
        self.wait_for_completion()
        log.debug(f"Homed: KDC101 device '{self.serialno}'")

    def move_to(self, pos):
        """
        Move the device to the specified position (index).

        The motor may need to be homed before a position can be set.

        Parameters
        ----------
        index : int
            The position in device units.
        block : bool, optional
            Blocks code until move is completed (default True).
        """
        log.debug(f"Moving to position '{pos}' (KDC101 {self.serialno})")
        status = kcdc.CC_MoveToPosition(
            self._serialno,
            c_int(self._real_value_to_du(pos, 0)))
        check_error(status)
        log.debug(f"Awaiting move completion (KDC101 {self.serialno})")
        self.wait_for_completion(id="moved")
        log.debug(f"Move completed (KDC101 {self.serialno})")

    # def move_to_unblocked(self, pos):
    #     """
    #     Move the device to the specified position (index).

    #     The motor may need to be homed before a position can be set.

    #     Parameters
    #     ----------
    #     index : int
    #         The position in device units.
    #     """
    #     status = kcdc.CC_MoveToPosition(
    #         self._serialno,
    #         c_int(self._real_value_to_du(pos, 0)))
    #     check_error(status)

    # @oneway
    def move_by(self, displacement):
        """
        Move the motor by a relative amount.

        Parameters
        ----------
        displacement : int
            The (signed) displacement in real units.
        """
        log.debug(f"Moving by {displacement} (KDC101 '{self.serialno}')")
        status = kcdc.CC_MoveRelative(
            self._serialno,
            c_int(self._real_value_to_du(displacement, 0)))
        check_error(status)
        self.wait_for_completion(id="moved")

    # @oneway
    def move_continuous(self, direction="forward"):
        """
        Moves the motor at a constant velocity in the specified direction.

        Move Continuous will attempt to obey the limits set on min_pos and 
        max_pos, but as these moves rely on position information feedback from 
        the device to detect if the travel is exceeding the limits, the device 
        will stop, but it is likely to overshoot the limit, especially at 
        high velocity.


        Parameters
        ----------
        direction : string
            The direction to move the motor. Acceptable values are ``forward``
            (default) and ``backward``. Sense can be reversed by calling 
            :py:func:``reverse``.
        """
        log.debug(f"Move continuous in direction '{direction}' (KDC101 '{self.serialno}')")
        if direction == "forward":
            direction = kcdc.MOT_Forwards
        elif direction == "backward":
            direction = kcdc.MOT_Reverse
        else:
            raise ValueError("direction '{}' unrecognized".format(direction))

        status = kcdc.CC_MoveAtVelocity(self._serialno, direction)
        try:
            check_error(status)
        except KinesisMotorError as e:
            # If it's just an invalid position error, we can ignore it
            if e.errcode == 38:
                pass
            else:
                raise e

    # @oneway
    def jog(self, direction, block: bool = True):
        """
        Jogs the motor using either stepped or continuous, 
        depending on what the jog mode is set to.

        Jog (continuous) will attempt to obey the limits set on min_pos and 
        max_pos, but as these moves rely on position information feedback from 
        the device to detect if the travel is exceeding the limits, the device 
        will stop, but it is likely to overshoot the limit, especially at 
        high velocity.

        Parameters
        ----------
        direction : string
            The direction to move the motor. Acceptable values are ``forward``
            and ``backward``. Sense can be reversed by calling 
            :py:func:``reverse``.
        block : bool, optional
            Blocks code until move is completed (default True).
        """
        log.debug(f"Jogging in direction '{direction}', blocking '{block}'(KDC101 '{self.serialno}')")
        c_dir = kcdc.MOT_TravelDirection
        if direction == "forward":
            c_dir = kcdc.MOT_Forwards
        elif direction == "backward":
            c_dir = kcdc.MOT_Reverse
        else:
            raise ValueError("direction '{}' unrecognized".format(direction))

        status = kcdc.CC_MoveJog(self._serialno, c_dir)
        check_error(status)
        if (self.jog_mode == "stepped"):
            if block:
                self.wait_for_completion("moved")

    # @oneway
    def stop(self, immediate=False):
        """
        Stops moving the motor either immediately or profiled.
        Default is profiled

        Parameters
        ----------
        immediate : bool
            When ``False`` (default) the motor uses a profiled stop.
            When ``True`` the motor uses an immediate stop.
        """
        stop_type = 'immediate' if immediate else 'profiled'
        log.debug(f"Stopping with stop type {stop_type} (KDC101 {self.serialno})")
        if immediate:
            status = kcdc.CC_StopImmediate(self._serialno)
        else:
            status = kcdc.CC_StopProfiled(self._serialno)
        check_error(status)
        self.wait_for_completion(id="stopped")
        log.debug(f"Stopped (KDC101 {self.serialno})")

    def close(self):
        """
        Closes the motor if the object has been instantiated.
        """
        log.info(f"KDC101 '{self.serialno}' closed.")
        if hasattr(self, "_serialno"):
            kcdc.CC_Close(self._serialno)
