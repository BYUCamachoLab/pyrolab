# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Errors
======

Custom errors for PyroLab.
"""


class PyroLabError(Exception):
    """Base class for all PyroLab exceptions."""
    pass


class CommunicationError(PyroLabError):
    """
    Error raised when there is a problem communicating with device
    """
    def __init__(self, message="Communication failed with device"):
        super().__init__(message)
    pass
