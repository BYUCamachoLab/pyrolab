# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Configuration Settings
----------------------

Default configuration settings for PyroLab.
"""

class Configuration:
    def __init__(self):
        self.reset()

    def reset(self):
        self.HOST = "localhost"
        self.NS_HOST = "localhost"

global_config = Configuration()
