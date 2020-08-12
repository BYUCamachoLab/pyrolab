# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
appdirs
-------

Default application directory settings for persisting data in PyroLab.
"""

from pathlib import Path
from appdirs import AppDirs

class Directories:
    """
    Provides pathlib.Path references to common datafile locations for PyroLab.

    Attributes
    ----------
    user_data_dir : pathlib.Path
        Return full path to the user-specific data dir for PyroLab.
    user_config_dir : pathlib.Path
        Return full path to the user-specific config dir for PyroLab.
    user_cache_dir : pathlib.Path
        Return full path to the user-specific cache dir for PyroLab.
    site_data_dir : pathlib.Path
        Return full path to the user-shared data dir forPyroLab.
    site_config_dir : pathlib.Path
        Return full path to the user-shared data dir for PyroLab.
        WARNING: Do not use this on Windows, instead use site_data_dir.
    user_log_dir : pathlib.Path
        Return full path to the user-specific log dir for PyroLab.

    Notes
    -----
    For more information on the implementation and opinions of the paths,
    see the ``appdirs`` repository (https://github.com/ActiveState/appdirs).
    """
    def __init__(self):
        self.paths = AppDirs("PyroLab", "CamachoLab")

    def __getattr__(self, name):
        try:
            path = getattr(self.paths, name)
            return Path(path)
        except AttributeError:
            raise AttributeError('No such program directory type.')

global_dirs = Directories()
