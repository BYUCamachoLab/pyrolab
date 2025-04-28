# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Motorized Precision Rotation Stage
==================================

Submodule containing drivers for the ThorLabs PRM1Z8 rotational stage, driven
by the KDC101 motor controller.

.. attention::

   Windows only.

   Requires ThorLabs Kinesis software. Download it at `thorlabs.com`_.

   .. _thorlabs.com: https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=10285

.. admonition:: Dependencies
   :class: note

   thorlabs_kinesis (:ref:`installation instructions <Thorlabs Kinesis Package>`)

.. tip::

   If you are using the remote functionalities of PyroLab, you may see the
   error ``RuntimeError: FT_DeviceNotFound`` when calling functions on objects
   inheriting from KDC101. This sometimes occus when you forget to call
   ``autoconnect()`` before trying to use the device.
"""

from pyrolab.api import behavior, expose
from pyrolab.drivers.motion.kinesis.kdc101 import KDC101, HomingMixin


@behavior(instance_mode="single")
@expose
class PRM1Z8(KDC101, HomingMixin):
    """
    A PRM1Z8 precision motorized rotation stage controlled by a KCube DC Servo
    motor.

    Parameters
    ----------
    serialno : int
        The serial number of the device to connect to.
    polling : int
        The polling rate in milliseconds.
    home : bool
        True tells the device to home when initializing
    """

    pass
