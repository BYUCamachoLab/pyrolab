# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Pure Photonics Tunable Laser PPCL551
--------------------------------

Driver for the Pure Photonics PPCL551 Tunable Laser

Contributors
 * David Hill (https://github.com/hillda3141)

Original repo: https://github.com/BYUCamachoLab/pyrolab
Based on code provided by Pure Photonics: https://www.pure-photonics.com/s/ITLA_v3-CUSTOMER.PY

.. note::

   The Pure Photonic drivers, which among other things, makes the USB 
   connection appear as a serial port, must be installed.
"""

from Pyro5.api import expose

from pyrolab.laser.pplaser import PurePhotonicsTunableLaser


@expose
class PPCL550(PurePhotonicsTunableLaser):
    """
    Driver for a Pure Photonic PPCL551 series laser.

    The laser must already be physically powered and connected to a USB port
    of some host computer, whether that be a local machine or one hosted by 
    a PyroLab server. Methods such as :py:func:`on` and :py:func:`off` will 
    simply turn the laser diode on and off, not the laser itself.

    Attributes
    ----------
    MINIMUM_WAVELENGTH : float
        The minimum wavelength of the laser in nanometers (value 1572).
    MAXIMUM_WAVELENGTH : float
        The maximum wavelength of the laser in nanometers (value 1609).
    MINIMUM_POWER_DBM : float
        The minimum power of the laser in dBm (value 7).
    MAXIMUM_POWER_DBM : float
        The maximum power of the laser in dBm (value 13.5).
    """

    MINIMUM_WAVELENGTH = 1572
    MAXIMUM_WAVELENGTH = 1609
    MINIMUM_POWER_DBM = 7
    MAXIMUM_POWER_DBM = 13.5
