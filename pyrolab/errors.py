# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Errors
------

PyroLab errors and exceptions.
"""


class PyroLabError(Exception):
    """Generic base class for PyroLab errors."""
    pass

class CommunicationError(PyroLabError):
    """An error in network communications."""
    pass
