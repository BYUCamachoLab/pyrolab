# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Errors
======

Custom errors for PyroLab.

PyroLab will only ever raise Python builtin exceptions or the errors listed
here. Remote tracebacks, however, may contain other exceptions. See each 
service's documentation for exceptions that may be raised by that service.
"""

from Pyro5.errors import PyroError


class PyroLabError(PyroError):
    """Base class for all PyroLab exceptions."""
    pass


class CommunicationError(PyroLabError):
    """
    Error raised when there is a problem communicating with device
    """
    def __init__(self, message="Communication failed with device"):
        super().__init__(message)
    pass
