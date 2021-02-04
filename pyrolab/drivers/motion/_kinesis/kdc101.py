# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
KDC101
------

Submodule that implements the basic functionality of the KCube DC Servo.

Contributors
 * Sequoia Ploeg (https://github.com/sequoiap)

Kinesis controllers are only available on Windows machines. Proxies from
other operating systems can however call Pyro services freely.

ThorLabs Kinesis should be installed, see ThorLabs' website to download.
"""

import time
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

from thorlabs_kinesis import kcube_dcservo as kcdc
from thorlabs_kinesis._utils import c_word, c_dword

from pyrolab.drivers.motion._kinesis import KinesisInstrument, ERROR_CODES
from pyrolab.api import expose


KCube_DC_Servo_Device_ID = 27

def check_error(status):
    if status != 0:
        raise RuntimeError(ERROR_CODES[status])

if kcdc.TLI_BuildDeviceList() == 0:
    size = kcdc.TLI_GetDeviceListSize()
    if size > 0:
        serialnos = create_string_buffer(10 * size)
        status = kcdc.TLI_GetDeviceListByTypeExt(serialnos, 10 * size, KCube_DC_Servo_Device_ID)
        check_error(status)

class HomingMixin:
    def home(self, block=True):
        kcdc.CC_Home(self._serialno)
        if block:
            self.wait_for_completion()

# TODO: Are requests necessary when polling is active?
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
        The serial number as a Python string.
    homed : bool
        Not sure what this is... but looks like it's a bool describing whether or not the device is homeable
    backlash : int
        The backlash setting (used to control hysteresis) in device units.
    velocity : int
        The homing velocity in device units. It is always a positive integer.
    
    """
    def __init__(self, serialno: str, polling=200, home=False):
        self.home=home
        self.serialno = serialno
        self._serialno = c_char_p(bytes(str(serialno), "utf-8"))
        check_error(kcdc.CC_Open(self._serialno))
        self.backlash = kcdc.CC_GetBacklash(self._serialno)
        self.velocity = kcdc.CC_GetHomingVelocity(self._serialno)

        # Get and store device info
        self._device_info = kcdc.TLI_DeviceInfo()
        kcdc.TLI_GetDeviceInfo(self._serialno, byref(self._device_info))

        kcdc.CC_LoadSettings(self._serialno)

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

        self.accel_param, self.vel_param = c_int(), c_int()
        kcdc.CC_GetJogVelParams(self._serialno, byref(self.accel_param), byref(self.vel_param))
        pos = kcdc.CC_GetPosition(self._serialno)
        
        # The following are in device units
        # TODO: Decide which min and max are correct.
        self._max_pos = kcdc.CC_GetStageAxisMaxPos(self._serialno)
        self._min_pos = kcdc.CC_GetStageAxisMinPos(self._serialno)

        # TODO: Do we need to save these?
        stepsPerRev = c_double()
        gearBoxRatio = c_double()
        pitch = c_double()
        check_error(kcdc.CC_GetMotorParamsExt(self._serialno, byref(stepsPerRev), byref(gearBoxRatio), byref(pitch)))




    def _du_to_real_value(self, du, unit_type):
        """
        Converts a device unit to a real world unit.

        Parameters
        ----------
        du : int
            The value in device units.
        unit_type : int
            The type of unit being converted; ``0`` for distance, ``1`` for 
            velocity, or ``2`` for acceleration.
        """
        real_unit = c_double()
        status = kcdc.CC_GetRealValueFromDeviceUnit(self._serialno, c_int(du), byref(real_unit), c_int(unit_type))
        check_error(status)
        return real_unit.value

    def _real_value_to_du(self, real, unit_type):
        """
        Parameters
        ----------
        real : float
            The value to be converted to device units.
        unit_type : int
            The type of unit being converted; ``0`` for distance, ``1`` for 
            velocity, or ``2`` for acceleration.
        """
        device_unit = c_int()
        status = kcdc.CC_GetDeviceUnitFromRealValue(self._serialno, c_double(real), byref(device_unit), c_int(unit_type))
        check_error(status)
        return device_unit.value

    @property
    def backlash(self):
        """
        The backlash setting (used to control hysteresis) in real units.
        """
        backlash = kcdc.CC_GetBacklash(self._serialno)

        return self._du_to_real_value(backlash, 0)

    @backlash.setter
    def backlash(self, val):
        """
        Parameters
        ----------
        val : float
            The valuse of the backlash setting in real units
        """
        status = kcdc.CC_SetBacklash(self._serialno, c_long(val))
        check_error(status)
        self.backlash = val

    @property
    def homing_velocity(self):
        """
        The homing velocity in device units. It is always a positive integer.
        """
        velocity = kcdc.CC_GetHomingVelocity(self._serialno)
        return velocity.value

    @homing_velocity.setter
    def homing_velocity(self, velocity):
        status = kcdc.CC_SetHomingVelocity(self._serialno, c_uint(velocity))
        check_error(status)

    @property
    def jog_mode(self):
        """
        The jog mode, either ``stepped`` (fixed distance, single step) or 
        ``continuous`` (move continuously until stopped).
        """
        jog_mode = kcdc.MOT_JogModes()
        stop_mode = kcdc.MOT_StopModes()
        status = kcdc.CC_GetJogMode(self._serialno, byref(jog_mode), byref(stop_mode))
        check_error(status)
        if jog_mode.value == kcdc.MOT_Continuous.value:
            return "continuous"
        elif jog_mode.value == kcdc.MOT_SingleStep.value:
            return "stepped"
        else:
            raise RuntimeError("Unexpected value received from Kinesis")

    @jog_mode.setter
    def jog_mode(self, jog_mode):
        """
        The jog mode, either ``stepped`` (fixed distance, single step) or 
        ``continuous`` (move continuously until stopped). 
        """
        c_jog_mode = kcdc.MOT_JogModeUndefined()
        c_stop_mode = kcdc.MOT_StopModeUndefined()
        stop_mode = self.stop_mode()

        if jog_mode == "continuous":
            c_jog_mode = kcdc.MOT_Continuous()
        elif jog_mode == "stepped":
            c_jog_mode = kcdc.MOT_SingleStep()
        if stop_mode == "immediate":
            c_stop_mode = kcdc.MOT_Immediate()
        elif stop_mode == "profiled":
            c_stop_mode = kcdc.MOT_Profiled()

        kcdc.CC_SetJogMode(self._serialno, c_jog_mode, c_stop_mode)

    @property
    def stop_mode(self):
        """
        The stop mode, either ``immediate`` (stops immediately) or 
        ``profiled`` (stops using the current velocity profile)
        """
        jog_mode = kcdc.MOT_JogModes()
        stop_mode = kcdc.MOT_StopModes()
        status = kcdc.CC_GetJogMode(self._serialno, byref(jog_mode), byref(stop_mode))
        check_error(status)
        if stop_mode.value == kcdc.MOT_Immediate:
            return "immediate"
        elif jog_mode.value == kcdc.MOT_Profiled.value:
            return "profiled"
        else:
            raise RuntimeError("Unexpected value received from Kinesis")

    @stop_mode.setter
    def stop_mode(self, stop_mode):
        """
        The stop mode, either ``immediate`` (stops immediately) or 
        ``profiled`` (stops using the current velocity profile)
        """
        c_jog_mode = kcdc.MOT_JogModeUndefined()
        c_stop_mode = kcdc.MOT_StopModeUndefined()
        jog_mode = self.jog_mode()

        if jog_mode == "continuous":
            c_jog_mode = kcdc.MOT_Continuous()
        elif jog_mode == "stepped":
            c_jog_mode = kcdc.MOT_SingleStep()
        if stop_mode == "immediate":
            c_stop_mode = kcdc.MOT_Immediate()
        elif stop_mode == "profiled":
            c_stop_mode = kcdc.MOT_Profiled()

        kcdc.CC_SetJogMode(self._serialno, c_jog_mode, c_stop_mode)

            

    @property
    def min_max_pos(self):
        """
        The stage axis position limits (min, max) in device units.
        """
        min_pos = c_int()
        max_pos = c_int()
        min_pos = kcdc.CC_GetStageAxisMinPos(self._serialno)
        max_pos = kcdc.CC_GetStageAxisMaxPos(self._serialno)
        return (self._du_to_real_value(min_pos, 0), self._du_to_real_value(max_pos, 0))

    @min_max_pos.setter
    def min_max_pos(self, min, max):
        """
        Sets the stage axis position limits. 

        This function sets the limits of travel for the stage.
        The implementation will depend upon the nature of the travel being requested 
        and the Soft Limits mode which can be obtained using soft_limits_mode(). 
        MoveAbsolute, MoveRelative and Jog (Single Step) will obey the Soft Limit Mode. 
        If the target position is outside the limits then either a full move, a partial 
        move or no move will occur. Jog (Continuous) and Move Continuous will attempt to 
        obey the limits, but as these moves rely on position information feedback from 
        the device to detect if the travel is exceeding the limits, the device will stop, 
        but it is likely to overshoot the limit, especially at high velocity.

        go_home() will always ignore the software limits.
        """
        status = kcdc.CC_SetStageAxisLimits(self._serialno, c_int(min), c_int(max))
        check_error(status)


    @property
    def soft_limits_mode(self):
        """
        The software limits mode 

        ``disallow``: Disable any move outside of the current travel 
        range of the stage.
        ``partial``: Truncate moves to within the current travel range 
        of the stage.
        ``all``: Allow all moves, regardless of whether they are within 
        the current travel range of the stage. 
        """
        mode = kcdc.CC_GetSoftLimitMode(self._serialno)
        if mode.value == kcdc.DisallowIllegalMoves.value:
            return "disallow"
        elif mode.value == kcdc.AllowPartialMoves.value:
            return "partial"
        elif mode.value == kcdc.AllowAllMoves.value:
            return "all"

    @soft_limits_mode.setter
    def soft_limits_mode(self, mode):
        """
        The software limits mode 

        ``disallow``: Disable any move outside of the current travel 
        range of the stage.
        ``partial``: Truncate moves to within the current travel range 
        of the stage.
        ``all``: Allow all moves, regardless of whether they are within 
        the current travel range of the stage. 
        """
        c_mode = kcdc.MOT_LimitsSoftwareApproachPolicy()
        if mode == "disallow":
            c_mode = kcdc.DisallowIllegalMoves()
        elif mode == "partial":
            c_mode = kcdc.AllowPartialMoves()
        elif mode == "all":
            c_mode = kcdc.AllowAllMoves()

        kcdc.CC_SetLimitsSoftwareApproachPolicy(self._serialno, c_mode)

    @property
    def move_velocity(self):
        accel = c_int()
        vel = c_int()
        status = kcdc.CC_GetVelParams(self._serialno, byref(accel), byref(vel))
        check_error(status)
        return vel.value

    @move_velocity.setter
    def move_velocity(self, velocity):
        status = kcdc.CC_SetVelParams(self._serialno, c_int(self.move_acceleration), c_int(self._real_value_to_du(velocity, 1)))
        check_error(status)

    @property
    def move_acceleration(self):
        # kcdc.CC_RequestVelParams(self._serialno)
        accel = c_int()
        vel = c_int()
        status = kcdc.CC_GetVelParams(self._serialno, byref(accel), byref(vel))
        check_error(status)
        return accel.value

    @move_acceleration.setter
    def move_acceleration(self, acceleration):
        status = kcdc.CC_SetVelParams(self._serialno, c_int(self._real_value_to_du(acceleration, 2)), c_int(self.move_velocity))
        check_error(status)

    def get_position(self):
        # status = kcdc.CC_RequestPosition(self._serialno)
        # time.sleep(0.1)
        #TODO: add functionality to move_to_position
        current_pos_du = kcdc.CC_GetPosition(self._serialno)
        return self._du_to_real_value(current_pos_du, 0)

    def wait_for_completion(self, id="homed"):
        """
        A blocking function to ensure a task has been finished.

        Used to for the following functions: homing, moving, stopping, 
        or updating limits. The id parameter must be specificed for 
        the correct operation ("homed", "moved", "stopped", or 
        "limit_updated").

        Parameters
        ----------
        id : string
            must be either "homed", "moved", "stopped", or "limit_updated"
            default is "homed"
        """
        message_type = c_word()
        message_id = c_word()
        message_data = c_dword()
        
        conditions = ["homed", "moved", "stopped", "limit_updated"]
        cond = conditions.index(id)

        kcdc.CC_WaitForMessage(self._serialno, byref(message_type), byref(message_id), byref(message_data))
        while int(message_type.value) != 2 or int(message_id.value) != cond:
            kcdc.CC_WaitForMessage(self._serialno, byref(message_type), byref(message_id), byref(message_data))

    def reverse(self):
        status = kcdc.CC_SetDirection(self._serialno, True)
        check_error(status)

    def identify(self):
        kcdc.CC_Identify(self._serialno)
    
    def go_home(self):
        """
        Takes the device home and sets self.homed to true
        """
        status = kcdc.CC_Home(self._serialno)
        check_error(status)
        self.homed = True
        self.wait_for_completion()

    def move_to(self, index):
        """
        Move the device to the specified position (index).

        The motor may need to be homed before a position can be set.

        Parameters
        ----------
        index : int
            The position in device units.
        """
        status = kcdc.CC_MoveToPosition(self._serialno, c_int(self._real_value_to_du(index)))
        check_error(status)
        self.wait_for_completion(id="moved")
    
    def move_by(self, displacement):
        """
        Move the motor by a relative amount.

        Parameters
        ----------
        displacement : int
            The (signed) displacement in real units.
        """
        status = kcdc.CC_MoveRelative(self._serialno, c_int(self._real_value_to_du(displacement)))
        check_error(status)
        self.wait_for_completion(id="moved")

    def move_continuous(self, direction="forward"):
        """
        Moves the motor at a constant velocity in the specified direction.

        Parameters
        ----------
        direction : string
            The direction to move the motor. Acceptable values are ``forward``
            (default) and ``backward``. Sense can be reversed by calling 
            :py:func:``reverse``.
        """
        if direction == "forward":
            direction = kcdc.MOT_Forwards
        elif direction == "backward":
            direction = kcdc.MOT_Reverse
        else: 
            raise ValueError("direction '{}' unrecognized".format(direction))

        status = kcdc.CC_MoveAtVelocity(self._serialno, direction)
        check_error(status)

    def jog(self):
        pass

    def stop(self, immediate=False):
        if immediate:
            status = kcdc.CC_StopImmediate(self._serialno)
        else:
            status = kcdc.CC_StopProfiled(self._serialno)
        check_error(status)
        self.wait_for_completion(id="stopped")

    def close(self):
        kcdc.CC_Close(self._serialno)
        