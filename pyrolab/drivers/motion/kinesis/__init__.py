# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Kinesis
=======

Hidden submodule that ensures ThorLabs Kinesis software is available.
"""

# Check if ThorLabs DLL's are saved in the configuration settings
# If not, search for ThorLabs DLL's
# If found, save their location to the configuration settings.
# Otherwise, ask the user to do something to locate them, perhaps some command line dealio.

import thorlabs_kinesis as tlk

from pyrolab.drivers.motion import Motion


class KinesisInstrument(Motion):
    pass


ERROR_CODES = {
    0: "FT_OK",
    1: "FT_InvalidHandle",
    2: "FT_DeviceNotFound",
    3: "FT_DeviceNotOpened",
    4: "FT_IOError",
    5: "FT_InsufficientResources",
    6: "FT_InvalidParameter",
    7: "FT_DeviceNotPresent",
    8: "FT_IncorrectDevice",

    16: "FT_NoDLLLoaded",
    17: "FT_NoFunctionsAvailable",
    18: "FT_FunctionNotAvailable",
    19: "FT_BadFunctionPointer",
    20: "FT_GenericFunctionFail",
    21: "FT_SpecificFunctionFail",

    32: "TL_ALREADY_OPEN",
    33: "TL_NO_RESPONSE",
    34: "TL_NOT_IMPLEMENTED",
    35: "TL_FAULT_REPORTED",
    36: "TL_INVALID_OPERATION",
    40: "TL_DISCONNECTING",
    41: "TL_FIRMWARE_BUG",
    42: "TL_INITIALIZATION_FAILURE",
    43: "TL_INVALID_CHANNEL",

    37: "TL_UNHOMED",
    38: "TL_INVALID_POSITION",
    39: "TL_INVALID_VELOCITY_PARAMETER",
    44: "TL_CANNOT_HOME_DEVICE",
    45: "TL_JOG_CONTINUOUS_MODE",
    46: "TL_NO_MOTOR_INFO",
    47: "TL_CMD_TEMP_UNAVAILABLE"
}
