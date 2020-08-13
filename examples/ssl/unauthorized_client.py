# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
2-Way SSL Client
----------------

...
"""

import Pyro5.api
import Pyro5.errors

import pyrolab
from pyrolab.client import get_proxy

pyrolab.config.SSL = False
# pyrolab.config.SSL_CACERTS = "../../certs/server_cert.pem"    # to make ssl accept the self-signed client cert
# pyrolab.config.SSL_CLIENTCERT = "../../certs/server_cert.pem"
# pyrolab.config.SSL_CLIENTKEY = "../../certs/server_key.pem"
# print("SSL enabled (2-way).")

uri = input("Server uri: ").strip()

with get_proxy(uri) as p:
    print(p)
    response = p.echo("client speaking")
    print("response:", response)
