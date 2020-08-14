# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Nameserver
----------------

Starts a basic nameserver on localhost.
"""

import pyrolab.api
pyrolab.api.config.reset(use_file=False)

pyrolab.api.start_ns_loop()
