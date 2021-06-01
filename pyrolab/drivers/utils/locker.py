# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Pyrolab Locker Class
--------------------

Utility for allowing classes to be locked and used by only one connection
at a time.
"""

import os
from Pyro5.api import expose
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
            temp = tempfile.NamedTemporaryFile(prefix = self.file_name, suffix = user, delete=False)
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
            prefixed = [filename for filename in os.listdir(tempfile.gettempdir()) if filename.startswith(self.file_name)]
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
        prefixed = [filename for filename in os.listdir(tempfile.gettempdir()) if filename.startswith(self.file_name)]
        if(len(prefixed) > 0):
            lock_status = True
        return lock_status
    
    def get_user(self):
        """
        Return the username or contents of the txt file.
        """
        exists = self.get_status()
        prefixed = [filename for filename in os.listdir(tempfile.gettempdir()) if filename.startswith(self.file_name)]
        if(len(prefixed) > 0):
            file_full = prefixed[0]
            name = file_full[len(self.file_name)+8:len(file_full)]
            return name
        else:
            return ""

# def lockable(obj):
#     """
#     Dynamically instantiates a new object with type the class of the object
#     appended by "Locker".

#     Parameters
#     ----------
#     obj : object
#         An instantiated object to be placed in a "Locker" class.

#     Returns
#     -------
#     DynamicLockable
#         An instantiated Locker object that contains the original object,
#         controlling access.
#     """
#     # This solution inspired by this Stack Overflow:
#     # https://stackoverflow.com/a/4723921/11530613

#     def __init__(self) -> None:
#         self._RESOURCE_LOCK = False
#         self._obj = obj

#     def __getattr__(self, attr):
#         """
#         Controls access to the locked object's attributes, intercepting them
#         if the lock is engaged.
#         """
#         ret = getattr(self._obj, attr)
#         if self._RESOURCE_LOCK:
#             raise Exception("Lock is engaged.")
#         return ret

#     def lock(self, user=""):
#         """
#         Locks access to the object's attributes.

#         Parameters
#         ----------
#         user : str, optional
#             The user who has locked the device. Useful when a device is locked
#             and another user wants to know who is using it.
#         """
#         self._RESOURCE_LOCK = True

#     def release(self):
#         """
#         Releases the lock on the object.
#         """
#         self._RESOURCE_LOCK = False

#     def islocked(self):
#         """
#         Returns the status of the lock.

#         Returns
#         -------
#         bool
#             True if the lock is engaged, False otherwise.
#         """
#         return self._RESOURCE_LOCK

#     # Dynamically create a new class that encloses the object.
#     DynamicLockable = type(
#         obj.__class__.__name__ + "Locker",
#         (object, ),
#         {
#             "__init__": __init__,
#             "__getattr__": __getattr__,
#             "lock": lock,
#             "release": release,
#             "islocked": islocked,
#         }
#     )
#     DL = expose(DynamicLockable)
#     return DL()
