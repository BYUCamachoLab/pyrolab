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

import pyrolab.api
pyrolab.api.config.reset(use_file=False)

pyrolab.api.start_ns_loop()
