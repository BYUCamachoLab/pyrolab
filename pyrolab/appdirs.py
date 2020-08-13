# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
appdirs
-------

Default application directory settings for persisting data in PyroLab.

Provides pathlib.Path references to common datafile locations for PyroLab.

Notes
-----
For more information on the implementation and opinions of the paths,
see the ``appdirs`` repository (https://github.com/ActiveState/appdirs).

Usage
-----
```
python3 -m pyrolab.appdirs -h
```
"""

from pathlib import Path
from appdirs import AppDirs


_paths = AppDirs("PyroLab", "CamachoLab")

# Return full path to the user-specific data dir for PyroLab.
user_data_dir = Path(_paths.user_data_dir)
# Return full path to the user-specific config dir for PyroLab.
user_config_dir = Path(_paths.user_config_dir)
# Return full path to the user-specific cache dir for PyroLab.
user_cache_dir = Path(_paths.user_cache_dir)
# Return full path to the user-shared data dir forPyroLab.
site_data_dir = Path(_paths.site_data_dir)
# Return full path to the user-shared data dir for PyroLab.
# WARNING: Do not use this on Windows, instead use site_data_dir.
site_config_dir = Path(_paths.site_config_dir)
# Return full path to the user-specific log dir for PyroLab.
user_log_dir = Path(_paths.user_log_dir)
