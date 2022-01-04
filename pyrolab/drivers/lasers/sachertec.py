# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
SacherTec Laser Driver
======================

Driver for a SacherTec Tunable Laser.

.. note::

   The SacherTec laser requires some DLL's in order to run. Get more info at 
   the links below:

    * https://support.maxongroup.com/hc/en-us/articles/360012695739
    * https://www.maxongroup.com/medias/sys_master/8823917281310.pdf

.. admonition:: Dependencies
   :class: note

   sacher-tec-500 (`repository <https://github.com/BYUCamachoLab/sacher-tec-500>`_)
"""

# TODO: Delegate the following to sacher_tec. PyroLab doesn't want to keep 
# track of driver DLL locations.
# import sys
# sys.path.insert(0, "C:\\Program Files\\SacherLasertechnik\\MotorMotion 2.1\\data")

from ctypes import *

from sacher_tec import epos_motor as epm
from sacher_tec._utils import c_dword, c_word

from pyrolab.drivers.lasers import Laser


class SacherTec500(Laser):
    """
    Driver for the SacherTec 500 laser.

    The laser must already be physically turned on and connected to a USB port
    of some host computer, whether that be a local machine or one hosted by 
    a PyroLab server.

    .. warning::

       This driver is underdeveloped and not in a functioning state at present.
    """
    def __init__(self) -> None:
        super().__init__()
        self.name = create_string_buffer(("EPOS2").encode('utf-8'))
        self.protocol = create_string_buffer(("MAXON SERIAL V2").encode('utf-8'))
        self.interface = create_string_buffer(("USB").encode('utf-8'))
        self.port = create_string_buffer(("USB0").encode('utf-8'))
        self.name_size = c_word(10)
        self.baudrate = c_dword(0)
        self.timeout = c_dword(0)
        self.node_id = c_word(0)
        self.dialog = c_int(3)
        self.error = c_dword(0)

    def connect(self) -> None:
        """
        Connects to the laser.
        """
        out = epm.VCS_OpenDeviceDlg(byref(self.error))
        print(out)
        print(self.error)

        handle = epm.VCS_OpenDevice(self.name, self.protocol, self.interface, self.port, byref(self.error))
        print(handle)
        print(self.error)

        out = epm.VCS_SetProtocolStackSettings(handle, self.baudrate, self.timeout, byref(self.error))
        print(out)
        print(self.error)

        out = epm.VCS_FindDeviceCommunicationSettings(
            byref(handle),          # c_int
            byref(self.name),       # c_char_p
            byref(self.protocol),   # c_char_p
            byref(self.interface),  # c_char_p
            byref(self.port),       # c_char_p
            self.name_size,         # c_word
            byref(self.baudrate),   # POINTER(c_dword)
            byref(self.timeout),    # POINTER(c_dword)
            byref(self.node_id),    # POINTER(c_word)
            self.dialog,            # POINTER(c_int)
            byref(self.error)       # POINTER(c_dword)
        )   # c_bool
        print(out)
        print(self.error)
        print(self.node_id)

    def close(self) -> None:
        """
        Closes the connection to the laser.
        """
        out = epm.VCS_CloseAllDevices(byref(self.error))

        print(out)
        print(self.error)
