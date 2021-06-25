# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Server Configuration
--------------------

Note the difference between the two ``servertypes``:

1. Threaded server
    Every proxy on a client that connects to the daemon will be assigned to a 
    thread to handle the remote method calls. This way multiple calls can 
    potentially be processed concurrently. This means your Pyro object may have 
    to be made thread-safe! 

2. Multiplexed server
    This server uses a connection multiplexer to process all remote method 
    calls sequentially. No threads are used in this server. It means only one 
    method call is running at a time, so if it takes a while to complete, all 
    other calls are waiting for their turn (even when they are from different 
    proxies).
"""

from typing import Optional

from pyrolab import SITE_CONFIG_DIR, SITE_DATA_DIR
from pyrolab.utils.configure import Configuration
from pyrolab.utils.profile import Profile
from pyrolab.utils.network import get_ip


SERVER_CONFIG_DIR = SITE_CONFIG_DIR / "server" / "config"
SERVER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

SERVER_DATA_DIR = SITE_DATA_DIR / "server" / "data"
SERVER_DATA_DIR.mkdir(parents=True, exist_ok=True)


class ServerConfiguration(Configuration):
    """
    Server configuration object.

    Note that for the ``host`` attribute, the string "public" will always be
    reevaluated to the computer's public IP address.

    Parameters
    ----------
    host : str, optional
        The hostname of the local server, or the string "public", which 
        is converted to the host's public IP address (default "localhost").
    ns_host : str, optional
        The hostname of the nameserver (default "localhost").
    ns_port : int, optional
        The port of the nameserver (default 9090).
    servertype : str, optional
        Either ``thread`` or ``multiplex`` (default "thread").
    """
    _valid_attributes = [
        'HOST', 'NS_HOST', 'NS_PORT', 'NS_BCPORT', 'NS_BCHOST', 'SERVERTYPE',
    ]

    def __init__(self,
                 host: str="localhost",
                 ns_host: str="localhost",
                 ns_port: int=9090,
                 ns_bcport: int=9091,
                 ns_bchost: Optional[bool]=None,
                 servertype: str="thread") -> None:
        super().__init__()
        # Be sure to use the ns_host as the host for the nameserver as well,
        # it's also a Pyro object.
        self.HOST = host
        self.NS_HOST = ns_host
        self.NS_PORT = ns_port
        self.NS_BCPORT = ns_bcport
        self.NS_BCHOST = ns_bchost
        self.SERVERTYPE = servertype

    def __setattr__(self, key, value):
        """
        Only known attributes are stored. Attributes shared with the Pyro5 
        config object are also set.
        """
        if key == "HOST" and value == "public":
            super().__setattr__(key, get_ip())
        else:
            super().__setattr__(key, value)


PROFILES_DIR = SERVER_CONFIG_DIR / "profiles"
PROFILES_SUFFIX = ".profile"
srv_profile = Profile(PROFILES_DIR, PROFILES_SUFFIX, ServerConfiguration)
