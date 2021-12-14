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


class PyroLabException(Exception):
    """Base class for all PyroLab exceptions."""
    pass


class PyroLabError(PyroLabException):
    """Base class for all PyroLab errors."""
    pass
