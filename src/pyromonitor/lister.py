from __future__ import annotations

import threading
from typing import List, NamedTuple
from datetime import datetime

from pyrolab.api import locate_ns, Proxy
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from pyromonitor.config import CONFIG


# List subapp
bp = Blueprint('lister', __name__)


# Globals
_timer = None
_status: List[InstrumentStatus] = []
_last_updated = None


class InstrumentStatus(NamedTuple):
    name: str
    uri: str
    description: str
    version: str
    status: str


def time_elapsed_human_readable(start: datetime=None, end: datetime=None) -> str:
    """
    Return the time delta of two times (or one and now) in plain English.

    Parameters
    ----------
    start : datetime
        The start time.
    end : datetime, optional
        The end time. Defaults to now.

    Returns
    -------
    str
        The time delta in plain English.
    """
    if not start:
        return "∞"
    elif end:
        delta = end - start
    else:
        delta = datetime.now() - start

    if delta.days > 0:
        return f"{delta.days} days"
    elif delta.seconds > 3600:
        return f"{delta.seconds // 3600} hours"
    elif delta.seconds > 120:
        return f"{delta.seconds // 60} minutes"
    elif delta.seconds > 60:
        return f"1 minute"
    else:
        return f"{delta.seconds} seconds"


def reset_timer() -> None:
    """
    Reset the timer that triggers a status refresh.

    Polling period is read from the configuration.
    """
    global _timer

    _timer = threading.Timer(CONFIG.polling, refresh_status)
    _timer.daemon = True
    _timer.start()


def refresh_status() -> None:
    """
    Refresh the availability status of every instrument known to the nameserver.

    This function has side effects, as it updates global variables that are
    made available to the page API.
    """
    global _last_updated
    global _status

    with locate_ns(CONFIG.nameserver) as ns:
        instruments: dict = ns.list(return_metadata=True) # {name: (uri, description)}
        instruments.pop("Pyro.NameServer") # no need to display the nameserver
        
    status = []
    for name, (uri, description) in instruments.items():
        description = list(description)[0]
        if len(description) > 80:
            description = description[:77] + "..."
        try:
            with Proxy(ns.lookup(name)) as p:
                version = p.pyrolab_version()
                status.append(InstrumentStatus(name, uri, description, version, "Available"))
        except ConnectionRefusedError as e:
            status.append(InstrumentStatus(name, uri, description, "", "Locked"))
        except Exception as e:
            status.append(InstrumentStatus(name, uri, description, "", "Unreachable"))

    _last_updated = datetime.now()
    _status = status
    reset_timer()


@bp.route('/', methods=["GET"])
def listall():
    global _last_updated
    global _status

    updated = f"{time_elapsed_human_readable(_last_updated)} ago"

    return render_template('base.html', status=_status, update_time=updated)


refresh_status()
