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
import atexit
import fileinput
import re
from typing import Callable, Iterable
from time import strptime
from pathlib import Path

# Check if Python version is supported
pyversion = sys.version_info
if pyversion < (3, 7, 0):
    raise Exception(
        "PyroLab requires Python 3.7+ (version "
        + platform.python_version()
        + " detected)."
    )


# Metadata
__name__ = "PyroLab"
__author__ = "CamachoLab"
__copyright__ = "Copyright 2020, The PyroLab Project"
__version__ = "0.3.2"
__license__ = "GPLv3+"
__maintainer__ = "Sequoia Ploeg"
__maintainer_email__ = "sequoia.ploeg@byu.edu"
__status__ = "Development"  # "Production"
__project_url__ = "https://github.com/sequoiap/pyrolab"
__forum_url__ = "https://github.com/sequoiap/pyrolab/issues"
__website_url__ = "https://camacholab.byu.edu/"


# Filter warnings
import warnings

warnings.filterwarnings("default", category=DeprecationWarning)
if "PYROLAB_HUSH_DEPRECATION" in os.environ:
    warnings.filterwarnings("ignore", category=DeprecationWarning)


# Configuration directories
# Old api deprecated in 3.11, new api added in 3.9
if pyversion < (3, 9, 0):
    base_path = pathlib.Path(__file__).resolve().parent
else:
    from importlib.resources import files

    base_path = files("pyrolab")
base_path = base_path / "data" / "local"

# Data directories
PYROLAB_DATA_DIR = pathlib.Path(base_path)
PYROLAB_DATA_DIR.mkdir(parents=True, exist_ok=True)

NAMESERVER_STORAGE = PYROLAB_DATA_DIR / "nameserver"
NAMESERVER_STORAGE.mkdir(parents=True, exist_ok=True)

PYROLAB_LOGDIR = PYROLAB_DATA_DIR / "logs"
PYROLAB_LOGDIR.mkdir(parents=True, exist_ok=True)
PYROLAB_MASTERLOG = PYROLAB_LOGDIR / "pyrolab.log"

LOCKFILE = PYROLAB_DATA_DIR / "pyrolabd.lock"
USER_CONFIG_FILE = PYROLAB_DATA_DIR / "user_configuration.yaml"
RUNTIME_CONFIG = PYROLAB_DATA_DIR / "runtime_config.yaml"


# Set up logging to file
import logging
import logging.handlers


def get_loglevel() -> int:
    loglevel = os.getenv("PYROLAB_LOGLEVEL", "INFO")
    try:
        loglevel = getattr(logging, loglevel.upper())
    except AttributeError:
        loglevel = logging.INFO
    return loglevel


if len(logging.root.handlers) == 0:
    logfile = PYROLAB_LOGDIR / f"pyrolab_{os.getpid()}.log"
    root = logging.getLogger()
    h = logging.handlers.RotatingFileHandler(logfile, "a", 30000, 10)
    f = logging.Formatter(
        "[%(asctime)s.%(msecs)03d] %(levelname)-8s %(process)-5s %(processName)-16s %(name)-20s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    h.setFormatter(f)
    root.addHandler(h)
    root.setLevel(get_loglevel())
    root.debug("PyroLab logging configured")


# Include remote traceback in local tracebacks
import Pyro5.errors

sys.excepthook = Pyro5.errors.excepthook


# Check for updates to PyroLab
try:
    import json
    import requests
    from requests.adapters import HTTPAdapter
    from packaging.version import parse

    url = "https://pypi.org/pypi/pyrolab/json"
    with requests.Session() as s:
        s.mount("https://pypi.org", HTTPAdapter(max_retries=3))
        resp = s.get(url).text

    v = json.loads(resp)["info"]["version"]
    curver = parse(__version__)
    latest = parse(v)

    log = logging.getLogger(__name__)

    if curver < latest:
        message = f"A new version of PyroLab is available (latest is {latest}, but {curver} is installed)."
        warnings.warn(message, stacklevel=2)
        log.info(message)
except:
    pass


def try_itr(func: Callable, itr: Iterable, *exceptions, **kwargs):
    """
    Tests a function on an iterable, yields iterable if no exception is raised.
    """
    for elem in itr:
        try:
            func(elem, **kwargs)
            yield elem
        except exceptions:
            pass


# @atexit.register
# def condense_logs():
#     """
#     Cleans up the logfile directory every once in a while.

#     Runs at exit or when "pyrolab down" is called. Condenses all process log
#     files into a single logfile that is sorted by timestamp.
#     """
#     f_names = list(PYROLAB_LOGDIR.glob("*.*"))
#     lines = list(fileinput.input(f_names))
#     t_fmt = "%Y-%m-%d %H:%M:%S.%f"  # format of time stamps
#     t_pat = re.compile(r"\[(.+?)\]")  # pattern to extract timestamp
#     lines = list(
#         try_itr(
#             lambda l: strptime(t_pat.search(l).group(1), t_fmt), lines, AttributeError
#         )
#     )
#     with PYROLAB_MASTERLOG.open(mode="w") as f:
#         for l in sorted(lines, key=lambda l: strptime(t_pat.search(l).group(1), t_fmt)):
#             f.write(l)
#     if PYROLAB_MASTERLOG in f_names:
#         f_names.remove(PYROLAB_MASTERLOG)
#     for f in f_names:
#         f.unlink()
