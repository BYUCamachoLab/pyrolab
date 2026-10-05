# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Update Check
============

Checks PyPI for a newer release of PyroLab.

Only the command line interface runs this check, and at most once per
:py:data:`CHECK_INTERVAL`: the result (including a failed check) is cached in a
small JSON file, so an isolated lab network pays for at most one timeout a day.
Importing ``pyrolab`` never touches the network. Set the environment variable
``PYROLAB_NO_VERSION_CHECK`` to disable the check entirely.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import requests
from packaging.version import InvalidVersion, Version

from pyrolab.utils import atomic_write_text

log = logging.getLogger(__name__)

PYPI_URL = "https://pypi.org/pypi/pyrolab/json"
CHECK_INTERVAL = 24 * 60 * 60  # seconds
TIMEOUT = (2, 2)  # (connect, read) seconds
DISABLE_ENV_VAR = "PYROLAB_NO_VERSION_CHECK"


def fetch_latest_version() -> str:
    """
    Return the latest version of PyroLab published on PyPI.

    Raises
    ------
    requests.RequestException
        If PyPI cannot be reached within :py:data:`TIMEOUT`, or responds with
        an error.
    """
    resp = requests.get(PYPI_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()["info"]["version"]


def check_for_update(
    current: str, cache_file: Path, now: Optional[float] = None
) -> Optional[str]:
    """
    Return the latest PyPI version if it is newer than ``current``.

    PyPI is consulted only when the cached result in ``cache_file`` is older
    than :py:data:`CHECK_INTERVAL`, so a newer version is reported at most
    once per interval. Never raises: a disabled, skipped, or failed check
    returns None.

    Parameters
    ----------
    current : str
        The installed version.
    cache_file : Path
        Where to record when the check last ran and what it found.
    now : float, optional
        The current time as a Unix timestamp (default ``time.time()``).

    Returns
    -------
    str or None
        The newer version, or None if there is nothing to report.
    """
    if DISABLE_ENV_VAR in os.environ:
        return None
    now = time.time() if now is None else now

    try:
        last_checked = json.loads(cache_file.read_text())["checked"]
        if 0 <= now - last_checked < CHECK_INTERVAL:
            return None
    except (OSError, ValueError, KeyError, TypeError):
        pass  # missing or unreadable cache: check now

    try:
        latest = fetch_latest_version()
    except Exception as e:
        log.debug("PyPI version check failed: %s", e)
        latest = None

    # Record the attempt even when it failed, so an offline machine doesn't
    # retry (and wait for the timeout) on every command.
    try:
        atomic_write_text(cache_file, json.dumps({"checked": now, "latest": latest}))
    except OSError as e:
        log.debug("Could not write version check cache %s: %s", cache_file, e)

    if latest is None:
        return None
    try:
        return latest if Version(latest) > Version(current) else None
    except InvalidVersion:
        log.debug("Could not compare versions %r and %r", latest, current)
        return None
