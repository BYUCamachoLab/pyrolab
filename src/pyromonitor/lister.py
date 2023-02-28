from typing import NamedTuple
from threading import Timer

from pyrolab.api import locate_ns, Proxy
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from pyromonitor.config import CONFIG


bp = Blueprint('lister', __name__)


class InstrumentStatus(NamedTuple):
    name: str
    uri: str
    description: str
    version: str
    status: str


def refresh_status():
    with locate_ns(CONFIG.nameserver) as ns:
        instruments: dict = ns.list(return_metadata=True) # {name: (uri, description)}
        instruments.pop("Pyro.NameServer") # no need to display the nameserver
        
    status = []
    for name, (uri, description) in instruments.items():
        if len(description) > 80:
            description = description[:77] + "..."
        try:
            with Proxy(ns.lookup(name)) as p:
                version = p.pyrolab_version()
                status.append(InstrumentStatus(name, uri, description, version, "Available"))
        except ConnectionRefusedError as e:
            status.append(InstrumentStatus(name, uri, description, "", "Locked"))
        except Exception as e:
            print(e)
            status.append(InstrumentStatus(name, uri, description, "", "Unreachable"))

    return status


@bp.route('/', methods=["GET"])
def listall():
    status = refresh_status()

    return render_template('base.html', status=status, update_time="now")
