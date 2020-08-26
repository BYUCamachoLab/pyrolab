# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Configuration Settings
----------------------

Default configuration settings for PyroLab and methods for persisting 
configurations between settings or using YAML files.
"""

import configparser
import logging
from pathlib import Path
from typing import Union, Optional, Dict, Any

import Pyro5


_PYRO_CONFIG = {
    "HOST": "localhost", 
    "NS_HOST": "localhost",
    "NS_PORT": 9090,
    "NS_BCPORT": 9091,
    "NS_BCHOST": None,
    "SERVERTYPE": "thread",
}

_PYROLAB_CONFIG = {
    "BROADCAST": False,
}

_DEFAULT_CONFIG = {**_PYRO_CONFIG, **_PYROLAB_CONFIG}


class Configuration:
    """
    Available configuration items are shown here.
    
    Warning
    -------
    Do not edit the values directly in this module! They are the global 
    defaults. Instead, provide a valid configuration file to PyroLab.
    """
    __slots__ = list(_DEFAULT_CONFIG.keys())

    def __init__(self):
        self.reset()

    def reset(self, cfile: Optional[str] = None):
        """
        Reset configuration items to their default values.

        If a configuration file is specified, PyroLab will load and apply the
        configuration as specified in that file. If no file is provided, 
        PyroLab will check the default configuration file location. If it does
        not exist, the clean defaults are applied.

        Parameters
        ----------
        cfile : str, optional
            The path to a configuration file. Or, ``None`` to use the clean
            program defaults.
        """
        Pyro5.config.reset(use_environment=False)

        for key, value in _DEFAULT_CONFIG.items():
            setattr(self, key, value)

        if type(cfile) is str:
            self.load(Path(cfile))
            

    def __getitem__(self, key):
        """
        Allows dictionary-like access of configuration parameters.
        """
        return getattr(self, key)

    def __setitem__(self, key, value):
        """
        Allows dictionary-like setting of configuration parameters.
        """
        setattr(self, key, value)

    def __setattr__(self, key, value):
        """
        Attributes are converted to a string-safe, text-based form each 
        time they're set.
        """
        super().__setattr__(key, value)
        if key in Pyro5.config.__slots__:
            setattr(Pyro5.config, key, value)

    def _to_dict(self) -> Dict[str, Any]:
        """
        Returns this configuration as a regular Python dictionary.
        
        Returns
        -------
        dict
            The configuration as a Python dictionary.
        """
        return {item: getattr(self, item) for item in self.__slots__}

    def _from_dict(self, dictionary: Dict[str, Any]):
        for key, value in dictionary.items():
            if key in self.__slots__:
                setattr(self, key, value)
            else:
                raise AttributeError("Configuration has no attribute '{}'".format(key))

    def copy(self):
        """
        Creates an exact copy of the current configuration (but does not begin
        using it).
        
        Returns
        -------
        other : Configuration
            A configuration object with the exact values copied over.
        """
        other = object.__new__(Configuration)
        for item in self.__slots__:
            setattr(other, item, getattr(self, item))
        return other

    def load(self, filename: Union[str, Path]):
        """
        Load the configuration from a specified file.

        Parameters
        ----------
        filename : str
            Path to a YAML-formatted file containing program configuration.
        """
        with open(filename, 'r') as f:
            cfg = configparser.ConfigParser()
            cfg.read_file(f)

            pyro = cfg['pyro5']
            self.HOST = pyro.get('HOST')
            self.NS_HOST = pyro.get('NS_HOST')
            self.NS_PORT = pyro.getint('NS_PORT')
            self.NS_BCPORT = pyro.getint('NS_BCPORT')
            val = pyro.get('NS_BCHOST')
            self.NS_BCHOST = val if val != 'None' else None
            self.SERVERTYPE = pyro.get('SERVERTYPE')

            pyrolab = cfg['pyrolab']
            self.BROADCAST = pyrolab.getboolean('BROADCAST')

    def save(self, filename: Union[str, Path]):
        """
        Saves the current program configuration to the a specified file (but 
        does not reference that file for configuration).

        Parameters
        ----------
        filename : str
            The location to save the configuration file to.
        """
        with open(filename, 'w') as f:
            cfg = configparser.ConfigParser()
            cfg.read_dict({'pyro5': {key: str(getattr(self, key)) for key in _PYRO_CONFIG.keys()},
                           'pyrolab': {key: str(getattr(self, key)) for key in _PYROLAB_CONFIG.keys()}
            })
            cfg.write(f)

    def dump(self) -> str:
        """
        Dumps the program configuration to a dictionary-formatted string.

        Returns
        -------
        str
            The dumped configuration settings.
        """
        return self._to_dict()


global_config = Configuration()


def dump():
    print(global_config.dump())


if __name__ == "__main__":
    dump()
