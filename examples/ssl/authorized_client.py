# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
2-Way SSL Client
----------------

A client that with a security certificate and SSL enabled. Its request to 
connect to the remote daemon will be allowed.
"""

import pyrolab.api
pyrolab.api.config.reset(use_file=False)

pyrolab.api.config.SSL = True
# To make ssl accept the self-signed client cert:
pyrolab.api.config.SSL_CACERTS = "../../certs/server_cert.pem"
# Client certificates, for the server to accept this client:
pyrolab.api.config.SSL_CLIENTCERT = "../../certs/client_cert.pem"
pyrolab.api.config.SSL_CLIENTKEY = "../../certs/client_key.pem"
print("SSL enabled (2-way).")

uri = input("Server uri: ").strip()

with pyrolab.api.Proxy(uri) as p:
    response = p.echo("client speaking")
    print("response:", response)
