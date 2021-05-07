# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

from typing import Optional

from pyrolab import SITE_CONFIG_DIR
from pyrolab.utils.configure import Configuration
from pyrolab.utils.profile import Profile
from pyrolab.utils.network import get_ip


SERVER_DIR = SITE_CONFIG_DIR / "server"
SERVER_DIR.mkdir(parents=True, exist_ok=True)


class ServerConfiguration(Configuration):
    """
    Nameserver configuration object.

    Parameters
    ----------
    host : str
        The hostname of the nameserver.
    ns_host
    ns_autoclean : float
        The interval in seconds to run the autocleaner to remove stale 
        resources. If 0.0, autocleaner does not run (default).
    storage : str
        One of "memory" or "sql:sqlfile".
    """
    _valid_attributes = [
        'NS_HOST', 'NS_PORT', 'NS_BCPORT', 'NS_BCHOST', 'NS_AUTOCLEAN', 
        'STORAGE',
    ]

    def __init__(self,
                 host: str="localhost",
                 ns_host: str="localhost",
                 ns_port: int=9090,
                 ns_bcport: int=9091,
                 ns_bchost: Optional[bool]=None) -> None:
        super().__init__()
        # Be sure to use the ns_host as the host for the nameserver as well,
        # it's also a Pyro object.
        self.HOST = host
        self.NS_HOST = ns_host
        self.NS_PORT = ns_port
        self.NS_BCPORT = ns_bcport
        self.NS_BCHOST = ns_bchost


PROFILES_DIR = SERVER_DIR / "profiles"
PROFILES_SUFFIX = ".profile"
profile = Profile(PROFILES_DIR, PROFILES_SUFFIX, ServerConfiguration)

def create_public_host():
    name = 'auto'
    cfg = ServerConfiguration(
        host=get_ip()
    )
    