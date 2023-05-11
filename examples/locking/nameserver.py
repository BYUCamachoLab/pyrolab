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

from pyrolab.api import start_ns_loop
from pyrolab.configure import NameServerConfiguration

# Let's run our nameserver! It will use the default profile, which provides
# sensible defaults--running on 'localhost', default port 9090, etc.
start_ns_loop(NameServerConfiguration())
