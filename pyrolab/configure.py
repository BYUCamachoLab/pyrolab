# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Configuration Settings
----------------------

Default configuration settings for PyroLab.
"""

import logging
from pathlib import Path

import Pyro5
import yaml

from pyrolab import dirs


CONFIG_FILENAME = 'config.yaml'
LOGFILE_FILENAME = 'pyrolab.log'


class Configuration:
    """
    Available configuration items are shown here.
    
    Warning
    -------
    Do not edit the values directly in this module! They are the global 
    defaults. Instead, provide a valid configuration file to PyroLab.
    """
    __slots__ = [
        # Pyro5 Configuration Settings
        "HOST", 
        "NS_HOST", 
        "SSL", 
        "SSL_SERVERCERT",
        "SSL_SERVERKEY",
        "SSL_SERVERKEYPASSWD",
        "SSL_REQUIRECLIENTCERT",
        "SSL_CLIENTCERT",
        "SSL_CLIENTKEY",
        "SSL_CLIENTKEYPASSWD",
        "SSL_CACERTS",
        # PyroLab Configuration Settings
        "LOGFILE", 
        "LOGLEVEL", 
    ]

    def __init__(self):
        self.reset()

    def reset(self, use_file=True):
        """
        Reset configuration items to their default values.
        """
        # Pyro5 Configuration Settings
        self.HOST = "localhost"
        self.NS_HOST = "localhost"
        self.SSL = False
        self.SSL_SERVERCERT = ""
        self.SSL_SERVERKEY = ""
        self.SSL_SERVERKEYPASSWD = ""
        self.SSL_REQUIRECLIENTCERT = False
        self.SSL_CLIENTCERT = ""
        self.SSL_CLIENTKEY = ""
        self.SSL_CLIENTKEYPASSWD = ""
        self.SSL_CACERTS = ""
        # PyroLab Configuration Settings
        self.LOGFILE = str(dirs.user_log_dir / LOGFILE_FILENAME)
        self.LOGLEVEL = "ERROR"

        if use_file:
            # Look for configuration file
            cfile = dirs.user_config_dir / CONFIG_FILENAME
            if cfile.is_file():
                self.use_file(cfile)

        # Set configuration values relevant to Pyro5
        self._configure_pyro5()

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        if hasattr(self, key):
            if type(getattr(self, key)) == type(value):
                setattr(self, key, value)
            else:
                raise TypeError("expected type '{}', got '{}' instead.".format(type(self.__dict__[key]), type(value)))

    def _configure_pyro5(self):
        Pyro5.config.reset(use_environment=False)
        for item in self.__slots__:
            if item in Pyro5.config.__slots__:
                setattr(Pyro5.config, item, getattr(self, item))

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

    def to_dict(self):
        """
        Returns this configuration as a regular Python dictionary.
        
        Returns
        -------
        dict
            The configuration as a Python dictionary.
        """
        return {item: getattr(self, item) for item in self.__slots__}

    def from_dict(self, dictionary):
        for key, value in dictionary.items():
            if key in self.__slots__:
                if type(value) == type(getattr(self, key)):
                    setattr(self, key, value)
                else:
                    raise TypeError('Invalid configuration item type')
            else:
                raise ValueError('Invalid configuration item')

    def _to_yaml(self):
        """
        Converts the configuration object to a YAML format using the 
        dictionary representation of the object.
        """
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    def _from_yaml(self, cfg):
        """
        Sets the configuration object from a YAML formatted string by 
        converting to a dictionary and updating the object's keys.
        """
        self.from_dict(yaml.load(cfg, Loader=yaml.FullLoader))

    def use_file(self, filename):
        """
        Load the configuration from a specified file.

        Parameters
        ----------
        filename : str
            Path to a YAML-formatted file containing program configuration.
        """
        with open(filename, 'r') as f:
            self._from_yaml(f.read())

    def save(self):
        """
        Save the program configuration to the default file (location is 
        platform dependent).
        """
        loc = dirs.user_config_dir / CONFIG_FILENAME
        if not loc.is_file():
            loc.parent.mkdir(parents=True, exist_ok=True)
            loc.touch()
        with open(loc, 'w') as f:
            f.write(self._to_yaml())

    def save_as(self, filename):
        """
        Saves the program configuration to the a specified file but does not
        reference that file for configuration.
        """
        with open(filename, 'w') as f:
            f.write(self._to_yaml())

    def dump(self):
        return self._to_yaml()


global_config = Configuration()


def dump():
    print(global_config.dump())


if __name__ == "__main__":
    dump()
