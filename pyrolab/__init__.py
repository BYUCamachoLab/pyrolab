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

if sys.version_info < (3, 6, 0):
    raise Exception(
        "PyroLab requires Python 3 (version "
        + platform.python_version()
        + " detected)."
    )

__author__ = "Sequoia Ploeg"
__copyright__ = "Copyright 2020, The PyroLab Project"
__version__ = "0.0.1dev0"
__license__ = "GPLv3+"
__maintainer__ = "Sequoia Ploeg"
__maintainer_email__ = "sequoia.ploeg@ieee.org"
__status__ = "Development" # "Production"
__project_url__ = "https://github.com/sequoiap/pyrolab"
__forum_url__ = "https://github.com/sequoiap/pyrolab/issues"
# __trouble_url__ = __project_url__ + "/wiki/Troubleshooting-Guide"
__website_url__ = "https://camacholab.byu.edu/"


from pyrolab.configure import global_config as config


def _configure_logging():
    """Do some basic config of the logging module at package import time.
    The configuring is done only if the PYRO_LOGLEVEL env var is set.
    If you want to use your own logging config, make sure you do
    that before any Pyro imports. Then Pyro will skip the autoconfig.
    Set the env var PYRO_LOGFILE to change the name of the autoconfigured
    log file (default is pyro5.log in the current dir). Use '{stderr}' to
    make the log go to the standard error output."""
    import logging

    if config.LOGLEVEL == "NOTSET":
        # Disable PyroLab logging.
        log = logging.getLogger("PyroLab")
        log.setLevel(9999)
    else:
        levelvalue = getattr(logging, config.LOGLEVEL.upper())
        if len(logging.root.handlers) == 0:
            if config.LOGFILE != "":
                loc = pathlib.Path(config.LOGFILE)
                if not loc.is_file():
                    loc.parent.mkdir(parents=True, exist_ok=True)
                    loc.touch()
            logging.basicConfig(
                level=levelvalue,
                filename=None if config.LOGFILE == "" else config.LOGFILE,
                datefmt="%Y-%m-%d %H:%M:%S",
                format="[%(asctime)s.%(msecs)03d,%(name)s,%(levelname)s] %(message)s"
            )
            log = logging.getLogger("PyroLab")
            log.info("PyroLab log configured using built-in defaults, level=%s", logging.getLevelName(levelvalue))

_configure_logging()
