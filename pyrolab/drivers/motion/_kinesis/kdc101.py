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


KCube_DC_Servo_Device_ID = 27

def check_error(status):
    if status.value != 0 and status.value in ERROR_CODES.keys():
        raise RuntimeError(ERROR_CODES[status.value])

if kcdc.TLI_BuildDeviceList() == 0:
    size = kcdc.TLI_GetDeviceListSize()
    if size > 0:
        serialnos = create_string_buffer(10 * size)
        status = kcdc.TLI_GetDeviceListByTypeExt(serialnos, 10 * size, KCube_DC_Servo_Device_ID)
        check_error(status)

class HomingMixin:
    def home(self):
        kcdc.CC_Home(self._serialno)
        self.wait_for_completion()

# TODO: Are requests necessary when polling is active?
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
    """
    def __init__(self, serialno, polling=200, home=False):
        self._serialno = c_char_p(bytes(str(serialno), "utf-8"))

        # Get and store device info
        self._device_info = kcdc.TLI_DeviceInfo()
        kcdc.TLI_GetDeviceInfo(self._serialno, byref(self._device_info))

        # Open communication with the device
        kcdc.CC_Open(self._serialno)
        kcdc.CC_StartPolling(self._serialno, c_int(polling))

        # Sleep while device initialization occurs
        time.sleep(3)

        # Clear the message queue
        kcdc.CC_ClearMessageQueue(self._serialno)

        # Is this necessary?
        self.wait_for_completion()

        if home:
            if not kcdc.CC_CanHome(self._serialno).value:
                self.homed = False
                raise RuntimeError("Device '{}' is not homeable.")
            else:
                status = kcdc.CC_Home(self._serialno)
                check_error(status)
                self.homed = True
        else:
            self.homed = False

        # The following are in device units
        self._max_pos = kcdc.CC_GetStageAxisMaxPosition(self._serialno)
        self._min_pos = kcdc.CC_GetStageAxisMinPosition(self._serialno)



    def __del__(self):
        kcdc.CC_Close(self._serialno)

    def _real_value_from_du(self, du, unit_type):
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
        status = kcdc.GetRealValueFromDeviceUnit(self._serialno, c_int(du), byref(real_unit), c_int(unit_type))
        check_error(status)
        return real_unit.value

    def _du_from_real_value(self, real, unit_type):
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
        status = kcdc.GetDeviceUnitFromRealValue(self._serialno, c_double(real), byref(device_unit), c_int(unit_type))
        check_error(status)
        return device_unit.value

    @property
    def serialno(self):
        return int(self._serialno.value.decode("utf-8"))

    @property
    def backlash(self):
        """
        The backlash setting (used to control hysteresis) in device units.
        """
        # kcdc.CC_RequestBacklash(self._serialno)
        # time.sleep(0.1)
        backlash = kcdc.CC_GetBacklash(self._serialno)
        return backlash

    @backlash.setter
    def backlash(self, val):
        status = kcdc.CC_SetBacklash(self._serialno, c_long(val))
        check_error(status)

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
        # TODO: Cross reference CC_GetJogMode docs and MOT_JogModes to make
        # sure the enum values are right!
        jog_mode = kcdc.MOT_JogModes()
        stop_mode = kcdc.MOT_StopModes()
        status = kcdc.CC_GetJogMode(self._serialno, byref(jog_mode), byref(stop_mode))
        if jog_mode.value == kcdc.MOT_Continuous.value:
            return "continuous"
        elif jog_mode.value == kcdc.MOT_SingleStep.value:
            return "stepped"
        else:
            raise RuntimeError("Unexpected value received from Kinesis")

    @jog_mode.setter
    def jog_mode(self, mode="stepped"):
        pass

    @property
    def jog_stop_mode(self):
        """
        The stop mode for jog moves, either ``immediate`` (motor stops 
        immediately) or ``profiled`` (motor stops using current velocity 
            profile).
        """
        pass

    @jog_stop_mode.setter
    def jog_stop_mode(self, mode="profiled"):
        pass

    @property
    def jog_step_size(self):
        pass

    @jog_step_size.setter
    def jog_step_size(self, step):
        pass

    @property
    def jog_acceleration(self):
        pass

    @jog_acceleration.setter
    def jog_acceleration(self):
        pass

    @property
    def jog_velocity(self):
        pass

    @jog_velocity.setter
    def jog_velocity(self, velocity):
        pass

    @property
    def motor_travel_limits(self):
        """
        Returns the minimum and maximum travel range constants for the current 
        stage. They are for user info only and do not reflect the current 
        travel range of the stage.

        Returns
        -------
        tuple : (float, float)
            The (min, max) positions of the stage in real world units.
        """
        min_position = c_double()
        max_position = c_double()
        status = kcdc.CC_GetMotorTravelLimits(self._serialno, byref(min_position), byref(max_position))
        check_error(status)
        return (min_position.value, max_position.value)

    @property
    def move_velocity(self):
        # kcdc.CC_RequestVelParams(self._serialno)
        accel = c_int()
        vel = c_int()
        status = kcdc.CC_GetVelParams(self._serialno, byref(accel), byref(vel))
        check_error(status)
        return vel.value

    @move_velocity.setter
    def move_velocity(self, velocity):
        status = kcdc.CC_SetVelParams(self._serialno, c_int(self.move_acceleration), c_int(velocity))
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
        status = kcdc.CC_SetVelParams(self._serialno, c_int(acceleration), c_int(self.move_velocity))
        check_error(status)

    @property
    def position(self):
        # status = kcdc.CC_RequestPosition(self._serialno)
        # time.sleep(0.1)
        position = kcdc.CC_GetPosition(self._serialno)
        return position

    def wait_for_completion(self):
        message_type = c_word()
        message_id = c_word()
        message_data = c_dword()

        kcdc.CC_WaitForMessage(self._serialno, byref(message_type), byref(message_id), byref(message_data))
        while int(message_type.value) != 2 or int(message_id.value) != 0:
            kcdc.CC_WaitForMessage(self._serialno, byref(message_type), byref(message_id), byref(message_data))

    def reverse(self):
        status = kcdc.CC_SetDirection(self._serialno, True)
        check_error(status)

    def move_absolute(self):
        pass

    def move(self, direction="forward"):
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

    def move_by(self, displacement):
        """
        Move the motor by a relative amount.

        Parameters
        ----------
        displacement : int
            The (signed) displacement in device units.
        """
        status = kcdc.CC_MoveRelative(self._serialno, c_int(displacement))
        check_error(status)

    def move_to(self, index):
        """
        Move the device to the specified position (index).

        The motor may need to be homed before a position can be set.

        Parameters
        ----------
        index : int
            The position in device units.
        """
        status = kcdc.CC_MoveToPosition(self._serialno, c_int(index))
        check_error(status)
    
    def stop(self, immediate=False):
        if immediate:
            status = kcdc.CC_StopImmediate(self._serialno)
        else:
            status = kcdc.CC_StopProfiled(self._serialno)
        check_error(status)

    def identify(self):
        kcdc.CC_Identify(self._serialno)
        