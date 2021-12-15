# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Errors
------

Custom errors for PyroLab.
"""
from Pyro5.errors import PyroError


class PyroLabException(PyroError):
    """Base class for all PyroLab exceptions."""
    pass

class CommunicationException(PyrolabException):
    """
    Error raised when there is a problem communicating with device
    """
    def __init__(self, message="Communication failed with device"):
        super().__init__(message)
    pass
