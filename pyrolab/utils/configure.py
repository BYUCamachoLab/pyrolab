# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

import Pyro5

class Configuration:
    """
    Inheritable PyroLab onfiguration object.

    Configuration settings that overlap with Pyro5 are automatically updated
    in Pyro5 when set in PyroLab.

    All configuration options should be included in the class attribute
    ``_valid_attributes``. Configuration options should be fully uppercased.
    In ``__init__()``, lowercase parameter names can be used but must be stored
    as uppercased attributes.
    """
    _valid_attributes = []

    def __init__(self) -> None:
        pass

    def __repr__(self):
        return f"<{self.__class__.__module__}.{self.__class__.__name__} object { {a: getattr(self, a) for a in self._valid_attributes} }>"

    def __setattr__(self, key, value):
        """
        Only known attributes are stored. Attributes shared with the Pyro5 
        config object are also set.
        """
        if key not in self._valid_attributes:
            raise Exception(f"invalid configuration parameter '{key}'")
        super().__setattr__(key, value)
        if key in Pyro5.config.__slots__:
            setattr(Pyro5.config, key, value)

    @classmethod
    def from_dict(cls, dictionary):
        """
        Case insensitive; all dictionary keys are converted to fully-uppercase
        before a match is attempted.
        """
        nc = cls()
        for k, v in dictionary.items():
            if k.upper() in nc._valid_attributes:
                setattr(nc, k, v)
            else:
                raise Exception(f"invalid configuration parameter '{v}'")
        return nc

    def to_dict(self):
        """
        Converts all key-value attributes to a dict.
        """
        return {param: getattr(self, param) for param in self._valid_attributes}
