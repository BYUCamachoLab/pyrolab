# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
DC Servo Motor Actuator
=======================

Submodule containing drivers for the ThorLabs Z8xxx linear stage, driven
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
class KMTS25E(KDC101, HomingMixin):
    """
    A Z825B motorized linear actuator controlled by a KCube DC Servo motor. 

    This stage has a travel range of 25 mm, submicron resolution, and a maximum
    velocity of 2.3 mm/s.

    Attributes
    ----------
    serialno : str
        The serial number as a string.
    homed : bool
        True if the device has been homed since being opened.
    backlash : float
        The backlash setting (used to control hysteresis) in real units
    homing_velocity : float
        The homing velocity in mm/s. It is always a positive number.
    jog_mode : str
        The jog mode can be either ``stepped`` (fixed distance, single step) or 
        ``continuous`` (move continuously until stopped).
    jog_step_size : float
        The distance to move in millimeters when jogging.
    stop_mode : str
        The stop mode, either ``immediate`` (stops immediately) or ``profiled`` 
        (stops, using the current velocity profile).
    max_pos : float
        The stage axis maximum position limit in millimeters.
    min_pos : float
        The stage axis minimum position limit in millimeters.
    soft_limits_mode : str
        The software limits mode 
        ``disallow``: Disable any move outside of the current travel range of 
        the stage.
        ``partial``: Truncate moves to within the current travel range of the 
        stage.
        ``all``: Allow all moves, regardless of whether they are within the 
        current travel range of the stage. 
    move_velocity : float
        The move velocity in mm/s. It is always a positive number.
    move_acceleration: float
        The move acceleration in real units. It is always a positive number.
    jog_velocity : float
        The jog velocity in mm/s. It is always a positive number.
    jog_acceleration : float
        The jog acceleration in real units. It is always a positive number.

    Notes
    -----
    See the `ThorLabs Z825B Product Page`_ for more details.

    .. _ThorLabs Z825B Product Page: https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=1883
    """
    pass