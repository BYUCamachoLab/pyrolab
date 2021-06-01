# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Server Resource Manager
-----------------------

The server resource manager handles the putting up and taking down of Daemons
for various instruments. To increase computer speed and processing 
capabilities in cases where multiple instruments are hosted from the same
computer, each instrument is created in its own Daemon using the 
Python ``multiprocessing`` module.
"""

import multiprocessing


class ResourceConfiguration:
    def __init__(self) -> None:
        pass
