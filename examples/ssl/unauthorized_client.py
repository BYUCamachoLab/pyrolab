# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
2-Way SSL Client
----------------

A client that doesn't have a certificate or SSL enabled. Its request to 
connect to the remote daemon will be denied.
"""

import pyrolab.api
pyrolab.api.config.reset(use_file=False)

pyrolab.config.SSL = False

uri = input("Server uri: ").strip()

with pyrolab.api.Proxy(uri) as p:
    response = p.echo("client speaking")
    print("response:", response)
