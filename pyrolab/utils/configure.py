# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

import logging
from typing import Any, Dict

import Pyro5


log = logging.getLogger(__name__)


class Configuration:
    """
    Inheritable PyroLab configuration object.

    Configuration settings that overlap with Pyro5 are automatically updated
    in Pyro5 when set in PyroLab. Arguments are case insensitive; any argument
    will be uppercased for comparison with the Pyro5 config object. Within the 
    configuration object itself, though, case is preserved.

    Parameters
    ----------
    kwargs : dict
        Key-value configuration pairs.

    Examples
    --------
    >>> from pyrolab.configure import Configuration
    >>> config = Configuration(host='localhost', port=9090)
    >>> config = Configuration(**{host: 'localhost', port: 9090})
    """
    def __init__(self, **kwargs) -> None:
        self.attrs = {}
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return f"<{self.__class__.__module__}.{self.__class__.__name__} object { self.attrs }>"

    def __setattr__(self, key, value):
        """
        Allows configuration variables to be set as attributes.
        
        Attributes shared with the Pyro5 config object are also set.
        """
        if key == "attrs":
            super().__setattr__(key, value)
        else:
            # All Pyro config options are fully uppercased
            if key.upper() in Pyro5.config.__slots__:
                setattr(Pyro5.config, key.upper(), value)
            else:
                log.info(f"Not a Pyro5 configuration option: {key}")
            self.attrs[key] = value

    def __getattr__(self, key):
        """
        Allows configuration variables to be accessed as attributes.
        """
        return self.attrs[key]

    def __setitem__(self, key, value):
        """
        Allows attributes to be set similar to a dictionary.
        """
        self.__setattr__(key, value)

    def __getitem__(self, key):
        """
        Allows attributes to be retrieved similar to a dictionary.
        """
        return getattr(self, key)

    @classmethod
    def from_dict(cls, dictionary):
        """
        Creates a configuration object from a dictionary.

        Equivalent to class instantiation using dictionary unpacking.

        Examples
        --------
        >>> # The following two are equivalent:
        >>> cfg = Configuration.from_dict({"host": "localhost", "port": 9090})
        >>> cfg = Configuration(**{"host": "localhost", "port": 9090})
        """
        return cls(**dictionary)

    def to_dict(self):
        """
        Converts all key-value attributes to a dict.
        """
        return {param: getattr(self, param) for param in self._valid_attributes}
