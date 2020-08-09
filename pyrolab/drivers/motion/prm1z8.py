# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
PRM1Z8
------

Submodule containing drivers for the ThorLabs PRM1Z8 rotational stage.
"""

from pyrolab.drivers.motion import Motion
from pyrolab.drivers.motion._kinesis.kdc101 import KDC101

class PRM1Z8(Motion, KDC101):
    pass
