# -*- coding: utf-8 -*-
# Copyright © 2020 PyroLab Project Contributors and others (see AUTHORS.txt).
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

A framework for using remote lab instruments as local resources built on Pyro5 
"""

import pathlib
import platform
import sys
import os

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
PYROLAB_DATA_DIR = pathlib.Path(_dirs.user_data_dir)
PYROLAB_DATA_DIR.mkdir(parents=True, exist_ok=True)

PYROLAB_CONFIG_DIR = pathlib.Path(_dirs.user_config_dir)
PYROLAB_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

PYROLABD_DATA = PYROLAB_DATA_DIR / "pyrolabd"
PYROLABD_DATA.mkdir(parents=True, exist_ok=True)

NAMESERVER_STORAGE = PYROLAB_DATA_DIR / "nameservers"
NAMESERVER_STORAGE.mkdir(parents=True, exist_ok=True)

CONFIG_DIR = PYROLAB_CONFIG_DIR / "config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

LOCKFILE = PYROLABD_DATA / "pyrolabd.lock"
USER_CONFIG_FILE = CONFIG_DIR / "user_configuration.yaml"


# Set up logging to file
import logging
logfile = os.getenv("PYROLAB_LOGFILE", PYROLAB_DATA_DIR / "pyrolab.log")
loglevel = os.getenv("PYROLAB_LOGLEVEL", "INFO")
try:
    loglevel = getattr(logging, loglevel.upper())
except AttributeError:
    loglevel = logging.INFO
logging.basicConfig(level=loglevel,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    filename=str(logfile),
                    filemode='a')
logging.debug("PyroLab started (logger configured).")


# Include remote traceback in local tracebacks
import Pyro5.errors
sys.excepthook = Pyro5.errors.excepthook


from multiprocessing import current_process
if current_process().name == 'MainProcess':
    PID = str(os.getpid()) + '_main'
    os.environ["PYROLAB_TOPLEVEL_PID"] = PID
else:
    PID = str(os.getpid()) + '_child'
