# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
2-Way SSL Server
----------------

A server that hosts a Pyro object that requires a client with a valid 
certificate before connection is allowed.
"""

from pathlib import Path

import pyrolab.api
from pyrolab.drivers.sample import SampleService
pyrolab.api.config.reset(use_file=False)


pyrolab.api.config.SSL = True
# Only allow connections from authorized clients.
pyrolab.api.config.SSL_REQUIRECLIENTCERT = True
# The server certificates to provide to the client:
pyrolab.api.config.SSL_SERVERCERT = "../../certs/server_cert.pem"
pyrolab.api.config.SSL_SERVERKEY = "../../certs/server_key.pem"
# To make ssl accept the self-signed client cert:
pyrolab.api.config.SSL_CACERTS = "../../certs/client_cert.pem"
print("SSL enabled (2-way).")


d = pyrolab.api.CertValidatingDaemon()
uri = d.register(SampleService)
print("server uri:", uri)
d.requestLoop()
