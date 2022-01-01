# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
DC Servo Motor Actuator
=======================

Submodule containing drivers for the ThorLabs Z8xxx linear stage, driven
by the KDC101 motor controller.

.. attention::
   Windows only (requires ThorLabs Kinesis).
"""

from pyrolab.api import behavior, expose
from pyrolab.drivers.motion.kinesis.kdc101 import KDC101, HomingMixin


@behavior(instance_mode="single")
@expose
class Z806(KDC101, HomingMixin):
    """
    A Z806 motorized linear actuator controlled by a KCube DC Servo motor. 

    This stage has a travel range of 6 mm, submicron resolution, and a maximum
    velocity of 2.3 mm/s.

    Parameters
    ----------
    serialno : int
        The serial number of the device to connect to.
    polling : int
        The polling rate in milliseconds.

    Notes
    -----
    See the `ThorLabs Z806 Product Page`_ for more details.

    .. _ThorLabs Z806 Product Page: https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=1881
    """
    pass


@behavior(instance_mode="single")
@expose
class Z812(KDC101, HomingMixin):
    """
    A Z812 and Z812B motorized linear actuator controlled by a KCube DC Servo motor. 

    This stage has a travel range of 12 mm, submicron resolution, and a maximum
    velocity of 2.3 mm/s.

    Parameters
    ----------
    serialno : int
        The serial number of the device to connect to.
    polling : int
        The polling rate in milliseconds.

    Notes
    -----
    See the `ThorLabs Z812 Product Page`_ for more details.

    .. _ThorLabs Z812 Product Page: https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=1882
    """
    pass


@behavior(instance_mode="single")
@expose
class Z825B(KDC101, HomingMixin):
    """
    A Z825B motorized linear actuator controlled by a KCube DC Servo motor. 

    This stage has a travel range of 25 mm, submicron resolution, and a maximum
    velocity of 2.3 mm/s.

    Parameters
    ----------
    serialno : int
        The serial number of the device to connect to.
    polling : int
        The polling rate in milliseconds.

    Notes
    -----
    See the `ThorLabs Z825B Product Page`_ for more details.

    .. _ThorLabs Z825B Product Page: https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=1883
    """
    pass
