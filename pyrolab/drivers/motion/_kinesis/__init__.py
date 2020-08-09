# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Kinesis
-------

Hidden submodule that ensures ThorLabs Kinesis software is available.
"""

# Check if ThorLabs DLL's are saved in the configuration settings
# If not, search for ThorLabs DLL's
# If found, save their location to the configuration settings.
# Otherwise, ask the user to do something to locate them, perhaps some command line dealio.

import thorlabs_kinesis as tlk

class KinesisInstrument:
    pass
