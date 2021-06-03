# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)


from typing import Dict

from Pyro5.client import Proxy
from pyrolab.api import locate_ns


class Client:
    def __init__(self, ns_host="localhost", ns_port=9090) -> None:
        self.ns = locate_ns(host="localhost")
        self._proxies: Dict[str, Proxy] = {}

    def list(self, return_metadata=False) -> Dict[str, str]:
        """
        Returns a dictionary of object registration names to Pyro URI's for
        all objects listed in the nameserver.
        """
        return self.ns.list(return_metadata=return_metadata)

    def remove(self, name):
        return self.ns.remove(name)

    def ping_ns(self):
        """
        Pings the nameserver.

        Returns
        -------
        bool
            True if no errors occurred during the ping.
        
        Raises
        ------
        Exception
            Raised if the connection is lost or any other errors occurred 
            during the ping.
        """
        self.ns.ping()
        return True

    def clean_ns(self):
        pass

    def lock(self, name):
        try:
            uri = self.ns.lookup(name)
            service = Proxy(uri)
            service.lock()
            self._proxies[name] = service
        except Exception:
            raise

    def release(self, name):
        if name not in self._proxies.keys():
            raise Exception(f"Client isn't the owner of the Proxy to '{name}'.")
        else:
            service = self._proxies[name]
            service._pyroConnection.close()
            del self._proxies[name]
