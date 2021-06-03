# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

from typing import Optional
from pyrolab import SITE_CONFIG_DIR, SITE_DATA_DIR
from pyrolab.utils.configure import Configuration
from pyrolab.utils.profile import Profile


NAMESERVER_CONFIG_DIR = SITE_CONFIG_DIR / "nameserver" / "config"
NAMESERVER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

NAMESERVER_DATA_DIR = SITE_DATA_DIR / "nameserver" / "data"
NAMESERVER_DATA_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_FILE = NAMESERVER_DATA_DIR / "storage.sql"


class NameserverConfiguration(Configuration):
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
        One of "memory" or "sql".
    """
    _valid_attributes = [
        'NS_HOST', 'NS_PORT', 'NS_BCPORT', 'NS_BCHOST', 'NS_AUTOCLEAN', 
        'STORAGE',
    ]

    def __init__(self,
                 ns_host: str="localhost",
                 ns_port: int=9090,
                 ns_bcport: int=9091,
                 ns_bchost: Optional[bool]=None,
                 ns_autoclean: float=0.0,
                 storage_type: str="sql",
                 storage_filename: str=f"{STORAGE_FILE}") -> None:
        super().__init__()
        # Be sure to use the ns_host as the host for the nameserver as well,
        # it's also a Pyro object.
        self.NS_HOST = ns_host
        self.NS_PORT = ns_port
        self.NS_BCPORT = ns_bcport
        self.NS_BCHOST = ns_bchost
        self.NS_AUTOCLEAN = ns_autoclean
        if storage_type == 'sql':
            self.STORAGE = storage_type + ":" + storage_filename
        else:
            self.STORAGE = storage_type


PROFILES_DIR = NAMESERVER_CONFIG_DIR / "profiles"
PROFILES_SUFFIX = ".profile"
ns_profile = Profile(PROFILES_DIR, PROFILES_SUFFIX, NameserverConfiguration)
