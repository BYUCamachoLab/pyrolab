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

import logging
import os
import platform
import sys

# Check if Python version is supported
pyversion = sys.version_info
if pyversion < (3, 11, 0):
    raise Exception(
        "PyroLab requires Python 3.11+ (version "
        + platform.python_version()
        + " detected)."
    )


# Metadata
__title__ = "PyroLab"
__author__ = "CamachoLab"
__copyright__ = "Copyright 2020, The PyroLab Project"
# pyproject.toml is the single source of the version (see `uv version`).
import importlib.metadata as _metadata

try:
    __version__ = _metadata.version("pyrolab")
except _metadata.PackageNotFoundError:  # source tree that isn't installed
    __version__ = "0.0.0+unknown"
__license__ = "GPLv3+"
__maintainer__ = "Sequoia Ploeg"
__maintainer_email__ = "sequoia.ploeg@byu.edu"
__status__ = "Development"  # "Production"
__project_url__ = "https://github.com/sequoiap/pyrolab"
__forum_url__ = "https://github.com/sequoiap/pyrolab/issues"
__website_url__ = "https://camacholab.byu.edu/"


# Where PyroLab keeps its files: per-user directories (see pyrolab.locations).
# Importing creates nothing; files and directories are created when written.
from pathlib import Path

from pyrolab.locations import LEGACY_DATA_DIR
from pyrolab.locations import locations as _find_locations

_locations = _find_locations()

PYROLAB_DATA_DIR = _locations.data_dir
NAMESERVER_STORAGE = _locations.data_dir / "nameserver"
PYROLAB_LOGDIR = _locations.log_dir
# The daemon's single log file; PYROLAB_LOGFILE overrides where it goes.
PYROLAB_LOGFILE = Path(
    os.environ.get("PYROLAB_LOGFILE") or PYROLAB_LOGDIR / "pyrolab.log"
)
USER_CONFIG_FILE = _locations.config_dir / "user_configuration.yaml"
LOCKFILE = _locations.state_dir / "pyrolabd.lock"
RUNTIME_CONFIG = _locations.state_dir / "runtime_config.yaml"
# Why the background daemon exited before it could serve requests, for `up`.
STARTUP_ERROR_FILE = _locations.state_dir / "pyrolabd_startup_error.txt"
# Records that files from a pre-0.5 install were copied (see pyrolab.locations).
LEGACY_MIGRATION_MARKER = _locations.state_dir / "legacy_files_copied.txt"
UPDATE_CHECK_FILE = _locations.cache_dir / "update_check.json"


# As a library, PyroLab leaves logging to the application: its loggers do
# nothing until the application (or PyroLab's own CLI and daemon, see
# pyrolab.logs) configures logging.
logging.getLogger(__name__).addHandler(logging.NullHandler())
