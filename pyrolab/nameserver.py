# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Nameserver
----------

Wrapped nameserver functions that references PyroLab configuration settings.
"""

import logging

import Pyro5.api

from pyrolab import config


log = logging.getLogger("pyrolab.nameserver")


def start_ns_loop(host=None, port=None, enableBroadcast=None, bchost=None, bcport=None,
                  unixsocket=None, nathost=None, natport=None, storage=None):
    """
    Utility function that starts a new Name Server and enters its requestloop.
    """
    if host is None:
        host = config.NS_HOST
    if port is None:
        port = config.NS_PORT
    if enableBroadcast is None:
        enableBroadcast = config.BROADCAST
    Pyro5.api.start_ns_loop(host=host, port=port, enableBroadcast=enableBroadcast,
        bchost=bchost, bcport=bcport, unixsocket=unixsocket, nathost=nathost,
        natport=natport, storage=storage)
