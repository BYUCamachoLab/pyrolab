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

import Pyro5.nameserver

from pyrolab.nameserver.configure import ns_profile as profile


log = logging.getLogger("pyrolab.nameserver")

# Inheriting from the Nameserver
class NameServer(Pyro5.nameserver.NameServer):
    pass

def start_ns_loop():
    """
    Utility function that starts a new Name Server and enters its requestloop.

    Loop can be shut down using ``ctrl+c``.
    """
    enableBroadcast = None
    Pyro5.nameserver.start_ns_loop(host=profile.NS_HOST, port=profile.NS_PORT, 
        enableBroadcast=enableBroadcast, bchost=profile.NS_BCHOST, 
        bcport=profile.NS_BCPORT, storage=profile.STORAGE)

def start_ns():
    """
    Utility fuction to quickly get a Nameserver daemon to be used in your own 
    event loops.
    
    Returns
    =======
    nameserverUri, nameserverDaemon, broadcastServer
        A tuple containing three pieces of information.
    """
    enableBroadcast = False
    return Pyro5.nameserver.start_ns(host=profile.NS_HOST, 
        port=profile.NS_PORT, enableBroadcast=enableBroadcast, 
        bchost=profile.BC_HOST, bcport=profile.BC_PORT,
        storage=profile.STORAGE)
