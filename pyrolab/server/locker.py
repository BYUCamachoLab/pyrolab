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

from pyrolab.server import expose


@expose
class Lockable:
    """
    New implementation of the Lockable instrument. Rejects new connections
    at the Daemon level, instead of at the object level which formerly checked
    for the existence of a "lock" file.
    """
    _RESOURCE_LOCK = False

    def __init__(self):
        self._RESOURCE_LOCK = False

    def lock(self, user=""):
        """
        Locks access to the object's attributes.

        Parameters
        ----------
        user : str, optional
            The user who has locked the device. Useful when a device is locked
            and another user wants to know who is using it.
        """
        self._RESOURCE_LOCK = True

    def release(self):
        """
        Releases the lock on the object.
        """
        self._RESOURCE_LOCK = False

    def islocked(self):
        """
        Returns the status of the lock.

        Returns
        -------
        bool
            True if the lock is engaged, False otherwise.
        """
        return self._RESOURCE_LOCK

def create_lockable(cls):
    """
    Dynamically create a new class that is also based on Lockable.

    Parameters
    ----------
    cls : class
        The class to be used as a template while dynamically creating a new
        class.
    
    Returns
    -------
    class
        A subclass that inherits from the original class and ``Lockable``.
    """
    DynamicLockable = type(
        cls.__name__ + "Locker",
        (cls, Lockable, ),
        {}
    )
    return DynamicLockable


# if __name__ == "__main__":
#     from pyrolab.drivers.sample import SampleService

#     ss = create_lockable(SampleService)
#     l = ss()
