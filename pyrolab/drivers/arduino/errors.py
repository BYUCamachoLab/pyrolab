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
from pyrolab.errors import PyroLabException

class UnknownBoardException(PyrolabException):
    """
    Error raised when the arduino board name is unknown or not supported
    """
    def __init__(self, message="Unknown board"):
        super().__init__(message)
    pass
