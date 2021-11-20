# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

from typing import Optional
from pyrolab import PYROLAB_CONFIG_DIR, PYROLAB_DATA_DIR
from pyrolab.utils.configure import Configuration
from pyrolab.utils.profile import Profile


NAMESERVER_CONFIG_DIR = PYROLAB_CONFIG_DIR / "nameserver" / "config"
NAMESERVER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

NAMESERVER_DATA_DIR = PYROLAB_DATA_DIR / "nameserver" / "data"
NAMESERVER_DATA_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_FILE = NAMESERVER_DATA_DIR / "storage.sql"


class NameserverConfiguration(Configuration):
    """
    Nameserver configuration object.

    Parameters
    ----------
    ns_host : str, optional
        Specify the hostname or ip address to bind the nameserver on. The 
        default is localhost; note that your name server will then not be 
        visible from the network. If the server binds on localhost, no 
        broadcast responder is started either. Make sure to provide a 
        hostname or ip address to make the name server reachable from 
        other machines, if you want that.
    ns_port : int, optional
        The port to bind the nameserver to (0=random). Default is 9090.
    ns_bchost : str, optional
        The hostname or ip address to bind the broadcast responder to. Default
        is None (no broadcast responder).
    ns_bcport : int, optional
        The port to bind the broadcast responder to. Default is 9091.
    ns_autoclean : float, optional
        The interval in seconds to run the autocleaner to remove stale 
        resources. If 0.0, autocleaner does not run (default).
    storage_type : str, optional
        One of "memory", "dbm", or "sql". Default "sql".
    storage_filename : str, optional
        The filename to use for the sqlite database. Default (when set to 
        ``None``) is to use an automaticlly created file in the PyroLab data
        directory.
    """
    def __init__(self,
                 ns_host: str="localhost",
                 ns_port: int=9090,
                 ns_bchost: Optional[bool]=None,
                 ns_bcport: int=9091,
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
