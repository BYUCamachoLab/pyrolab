from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from pyrolab.api import locate_ns, Proxy


bp = Blueprint('lister', __name__)#, url_prefix='/lister')

ns = locate_ns("camacholab.ee.byu.edu")
instruments: dict = ns.list(return_metadata=True)
instruments.pop("Pyro.NameServer") # no need to display the nameserver
for inst, vals in instruments.items():
    # TODO: Check if it's locked
    try:
        p = Proxy(ns.lookup(inst))
        p.autoconnect()
        instruments[inst] = *vals, "Available"
    except:
        instruments[inst] = *vals, "Unavailable"

@bp.route('/', methods=["GET"])
def listall():
    global instruments

    return render_template('base.html', instruments=instruments, list=list, update_time="now")
