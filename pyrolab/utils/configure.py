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
        self.pyro_attrs = {}
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        return f"<{self.__class__.__module__}.{self.__class__.__name__} object { {**self.attrs, **self.pyro_attrs} }>"

    def __setattr__(self, key, value) -> None:
        """
        Allows configuration variables to be set as attributes.
        
        Attributes shared with the Pyro5 config object are also set.
        """
        if key == "attrs" or key == "pyro_attrs":
            super().__setattr__(key, value)
        elif key.upper() in Pyro5.config.__slots__:
            self.pyro_attrs[key] = value
        else:
            self.attrs[key] = value

    def __getattr__(self, key) -> Any:
        """
        Allows configuration variables to be accessed as attributes.
        """
        if key in self.pyro_attrs:
            return self.pyro_attrs[key]
        elif key in self.attrs:
            return self.attrs[key]
        else:
            raise KeyError(f'{key}')

    def __setitem__(self, key, value) -> None:
        """
        Allows attributes to be set similar to a dictionary.
        """
        self.__setattr__(key, value)

    def __getitem__(self, key) -> Any:
        """
        Allows attributes to be retrieved similar to a dictionary.
        """
        return getattr(self, key)

    @classmethod
    def from_dict(cls, dictionary) -> 'Configuration':
        """
        Creates a configuration object from a dictionary.

        Equivalent to class instantiation using dictionary unpacking.

        Parameters
        ----------
        dictionary : dict
            Dictionary of key-value pairs.

        Returns
        -------
        Configuration
            Configuration object.

        Examples
        --------
        >>> # The following two are equivalent:
        >>> cfg = Configuration.from_dict({"host": "localhost", "port": 9090})
        >>> cfg = Configuration(**{"host": "localhost", "port": 9090})
        """
        return cls(**dictionary)

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts all key-value attributes to a dict.

        Returns
        -------
        dict
            Dictionary of all key-value attributes.
        """
        return {**self.attrs, **self.pyro_attrs}

    def update_pyro_config(self) -> None:
        """
        Sets all key-value attributes that are Pyro5 configuration options.
        """
        for key, value in self.pyro_attrs.items():
            if key.upper() in Pyro5.config.__slots__:
                # All Pyro config options are fully uppercased
                setattr(Pyro5.config, key.upper(), value)
            else:
                # Somehow a key was set that is not a Pyro config option
                log.warning(f"Not a Pyro5 configuration option: {key}")
