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
)
from ctypes.wintypes import DWORD, WORD

from thorlabs_kinesis import kcube_dcservo as kcdc
from thorlabs_kinesis._utils import c_word, c_dword

from pyrolab.drivers.motion._kinesis import KinesisInstrument, ERROR_CODES


KCube_DC_Servo_Device_ID = 27


if kcdc.TLI_BuildDeviceList() == 0:
    size = kcdc.TLI_GetDeviceListSize()
    serialnos = create_string_buffer(10 * size)
    kcdc.TLI_GetDeviceListByTypeExt(serialnos, 10 * size, KCube_DC_Servo_Device_ID)

class HomingMixin:
    def home(self):
        kcdc.CC_Home(self._serialno)
        self.wait_for_completion()

class KDC101(KinesisInstrument):
    """
    A KCube DC Servo motor. 

    Parameters
    ----------
    serialno : int
        The serial number of the device to connect to.
    polling : int
        The polling rate in milliseconds.
    """
    def __init__(self, serialno, polling):
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

    def __del__(self):
        kcdc.CC_Close(self._serialno)

    @property
    def serialno(self):
        return int(self._serialno.value.decode("utf-8"))

    @property
    def backlash(self):
        kcdc.CC_RequestBacklash(self._serialno)
        time.sleep(0.1)
        backlash = kcdc.CC_GetBacklash(self._serialno)
        return backlash

    @backlash.setter
    def backlash(self, val):
        status = kcdc.CC_SetBacklash(self._serialno, c_long(val))
        self.check_error(status)

    def wait_for_completion(self):
        message_type = c_word()
        message_id = c_word()
        message_data = c_dword()

        kcdc.CC_WaitForMessage(self._serialno, byref(message_type), byref(message_id), byref(message_data))
        while int(message_type.value) != 2 or int(message_id.value) != 0:
            kcdc.CC_WaitForMessage(self._serialno, byref(message_type), byref(message_id), byref(message_data))
    
    def stop(self, immediate=False):
        if immediate:
            status = kcdc.CC_StopImmediate(self._serialno)
        else:
            status = kcdc.CC_StopProfiled(self._serialno)
        self.check_error(status)

    def check_error(self, status):
        if status.value != 0 and status.value in ERROR_CODES.keys():
            raise RuntimeError(ERROR_CODES[status.value])
        