# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Pyrolab Locker Class
-----------------------------------------------
Driver for the Santec TSL-550 Tunable Laser.
Contributors
 * David Hill (https://github.com/hillda3141)
 * Sequoia Ploeg (https://github.com/sequoiap)
"""

import os
from os import path
import time
from Pyro5.api import expose
import pyrolab.api
import tempfile

@expose
class Locker():

    """
    This class "locks" a device by creating a text document named after it in
    the director C:\\LockedDevices. This directory must exist before exectuing
    this code. The txt file that it creates can be empty (no username given)
    or have a username as its content. Adding a name is often usefull so others
    can see who is using the device.
    """

    fileName = ""
    MASTER_PWD = "override"

    def __init__(self,deviceName):
        """
        Initialize the file name that we are dealing with, depending on the
        device name.
        """

        self.file_name = deviceName + "_LOCK"

    def lock(self,user=""):
        """
        Create the txt file and write the password inside, unless the file
        already exhists.
        """
        exists = self.get_status()
        if exists == True:
            return 1
        else:
            temp = tempfile.NamedTemporaryFile(prefix = self.file_name,
            suffix = user, delete=False)
            temp.close()
            return 1

    def release(self,user=""):
        """
        If the password that is inputed matches the content of the txt file,
        delete the file to unlock.
        """
        exists = self.get_status()
        if exists == True:
            directory = tempfile.gettempdir()
            prefixed = [filename for filename in os.listdir(tempfile.gettempdir())
            if filename.startswith(self.file_name)]
            file_full = prefixed[0]
            pwd = file_full[len(self.file_name)+8:len(file_full)]
            if (user == pwd or user == self.MASTER_PWD):
                del_file = directory + "\\" + file_full
                os.remove(del_file)
                return 1
            else:
                return 0
        else:
            return 1

    def get_status(self):
        """
        Return True if the file exists, false otherwise.
        """
        lock_status = False
        prefixed = [filename for filename in os.listdir(tempfile.gettempdir())
        if filename.startswith(self.file_name)]
        if(len(prefixed) > 0):
            lock_status = True
        return lock_status
    
    def get_user(self):
        """
        Return the username or contents of the txt file.
        """
        exists = self.get_status()
        prefixed = [filename for filename in os.listdir(tempfile.gettempdir())
        if filename.startswith(self.file_name)]
        if(len(prefixed) > 0):
            file_full = prefixed[0]
            name = file_full[len(self.file_name)+8:len(file_full)]
            return name
        else:
            return ""
