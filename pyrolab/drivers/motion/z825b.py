# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Z825B
-----

Submodule containing drivers for the ThorLabs Z825B linear stage.
"""

from pyrolab.drivers.motion import Motion
from pyrolab.drivers.motion._kinesis import KinesisInstrument

class Z825B(Motion, KinesisInstrument):
    pass
