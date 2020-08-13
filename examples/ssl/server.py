# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
2-Way SSL Server
----------------

...
"""

from pathlib import Path

import Pyro5.api

import pyrolab
from pyrolab.server import get_daemon

class Safe:
    @Pyro5.api.expose
    def echo(self, message):
        print("got message:", message)
        return "hi!"

pyrolab.config.SSL = True
pyrolab.config.SSL_REQUIRECLIENTCERT = True
pyrolab.config.SSL_SERVERCERT = str(Path("../../certs/server_cert.pem").resolve())
pyrolab.config.SSL_SERVERKEY = str(Path("../../certs/server_key.pem").resolve())
pyrolab.config.SSL_CACERTS = str(Path("../../certs/client_cert.pem").resolve())    # to make ssl accept the self-signed client cert
print("SSL enabled (2-way).")

# pyrolab.config.save()

d = get_daemon()
uri = d.register(Safe)
print("server uri:", uri)
d.requestLoop()
