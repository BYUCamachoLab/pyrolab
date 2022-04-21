# -*- coding: utf-8 -*-
# Copyright © 2020- PyroLab Project Contributors and others (see AUTHORS.txt).
# The resources, libraries, and some source files under other terms (see NOTICE.txt).
#
# This file is part of PyroLab.
#
# PyroLab is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyroLab is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyroLab. If not, see <https://www.gnu.org/licenses/>.

"""
PyroLab
=======

A framework for using remote lab instruments as local resources built on Pyro5.
"""

import os
import pathlib
import platform
import sys

if sys.version_info < (3, 7, 0):
    raise Exception(
        "PyroLab requires Python 3.7+ (version "
        + platform.python_version()
        + " detected)."
    )

__name__ = "PyroLab"
__author__ = "CamachoLab"
__copyright__ = "Copyright 2020, The PyroLab Project"
__version__ = "0.2.1"
__license__ = "GPLv3+"
__maintainer__ = "Sequoia Ploeg"
__maintainer_email__ = "sequoia.ploeg@byu.edu"
__status__ = "Development" # "Production"
__project_url__ = "https://github.com/sequoiap/pyrolab"
__forum_url__ = "https://github.com/sequoiap/pyrolab/issues"
__website_url__ = "https://camacholab.byu.edu/"


import warnings

warnings.filterwarnings("default", category=DeprecationWarning)
if "PYROLAB_HUSH_DEPRECATION" in os.environ:
    warnings.filterwarnings("ignore", category=DeprecationWarning)


# Hide a very annoying warnings from appnope about Python 3.12
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    import appnope
    appnope.nope()


from appdirs import AppDirs

_dirs = AppDirs(__name__, __author__)

# Data Directories
PYROLAB_DATA_DIR = pathlib.Path(_dirs.user_data_dir)
PYROLAB_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Configuration Directories
PYROLAB_CONFIG_DIR = PYROLAB_DATA_DIR / "config"
PYROLAB_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# User config file directory
CONFIG_DIR = PYROLAB_CONFIG_DIR / "user"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# Background daemon data directory
PYROLABD_DATA = PYROLAB_DATA_DIR / "pyrolabd"
PYROLABD_DATA.mkdir(parents=True, exist_ok=True)

NAMESERVER_STORAGE = PYROLAB_DATA_DIR / "nameservers"
NAMESERVER_STORAGE.mkdir(parents=True, exist_ok=True)

LOCKFILE = PYROLABD_DATA / "pyrolabd.lock"
USER_CONFIG_FILE = CONFIG_DIR / "user_configuration.yaml"
RUNTIME_CONFIG = PYROLABD_DATA / "runtime_config.yaml"
PYROLAB_LOGFILE = PYROLAB_DATA_DIR / "pyrolab.log"


# Set up logging to file
import logging
import logging.handlers


def get_loglevel() -> int:
    loglevel = os.getenv("PYROLAB_LOGLEVEL", "INFO")
    try:
        loglevel = getattr(logging, loglevel.upper())
    except AttributeError:
        loglevel = logging.INFO
    loglevel = logging.DEBUG
    return loglevel

if len(logging.root.handlers) == 0:    
    # This is not multiprocess safe, but it's not critical right now
    logfile = os.getenv("PYROLAB_LOGFILE", PYROLAB_LOGFILE)

    root = logging.getLogger()
    h = logging.handlers.RotatingFileHandler(logfile, 'a', 30000, 10)
    f = logging.Formatter('%(asctime)s.%(msecs)03d %(process)-5s %(processName)-10s %(name)-12s %(levelname)-8s %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
    # h.setFormatter(f)
    # root.addHandler(h)
    root.setLevel(get_loglevel())
    root.debug("PyroLab logging configured")


# Include remote traceback in local tracebacks
import Pyro5.errors

sys.excepthook = Pyro5.errors.excepthook
