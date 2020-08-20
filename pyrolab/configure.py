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

import logging
from pathlib import Path
from typing import Union, Optional, Dict, Any

import Pyro5
import yaml

from pyrolab import dirs as appdirs


CONFIG_FILENAME = 'config.yaml'
LOGFILE_FILENAME = 'pyrolab.log'


_DEFAULT_CONFIG = {
    # Pyro5 Configuration Settings
    "HOST": "localhost", 
    "NS_HOST": "localhost",
    "NS_PORT": 9090,
    "NS_BCPORT": 9091,
    "NS_BCHOST": None,
    "SERVERTYPE": "thread",
    "LOGFILE": appdirs.user_log_dir / LOGFILE_FILENAME,
    "LOGLEVEL": "ERROR",
    "SSL": False,
    "SSL_SERVERCERT": Path(""),
    "SSL_SERVERKEY": Path(""),
    "SSL_SERVERKEYPASSWD": "",
    "SSL_REQUIRECLIENTCERT": False,
    "SSL_CLIENTCERT": Path(""),
    "SSL_CLIENTKEY": Path(""),
    "SSL_CLIENTKEYPASSWD": "",
    "SSL_CACERTS": Path(""),
    # PyroLab Configuration Settings
    "BROADCAST": False,
}

def _textualize(key, value):
    if type(value) is Path:
        return str(value.resolve())
    elif type(value) not in [str, bool, int, float, type(None)]:
        return str(value)
    else:
        return value

def _objectify(key, value):
    try:
        T = type(_DEFAULT_CONFIG[key])
        if T == type(None) and value is not None:
            return value
        elif T == type(None) and value is None:
            return None
        else:
            return T(value)
    except KeyError:
        return value


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

    def reset(self, use_file: Optional[Union[str, bool]] = True):
        """
        Reset configuration items to their default values.

        If a configuration file is specified, PyroLab will load and apply the
        configuration as specified in that file. If no file is provided, 
        PyroLab will check the default configuration file location. If it does
        not exist, the clean defaults are applied.

        Parameters
        ----------
        use_file : bool or str, optional
            The path to a configuration file. Or, ``False`` to use the clean
            program defaults. If ``True`` or not specified, PyroLab searches
            for the default configuration file.
        """
        Pyro5.config.reset(use_environment=False)

        for key, value in _DEFAULT_CONFIG.items():
            setattr(self, key, value)

        if use_file is True:
            cfile = appdirs.user_config_dir / CONFIG_FILENAME
            if cfile.is_file():
                self.use_file(cfile)
        elif use_file is False:
            return
        elif type(use_file) is str:
            self.use_file(Path(use_file))
            

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

    def __getattribute__(self, name):
        """
        Attributes are stored in their string-safe, text-based form but
        cast as the appropriate type each time they're "gotten".
        """
        if name in _DEFAULT_CONFIG.keys():
            return _objectify(name, super().__getattribute__(name))
        return super().__getattribute__(name)

    def __setattr__(self, key, value):
        """
        Attributes are converted to a string-safe, text-based form each 
        time they're set.
        """
        value = _textualize(key, value)
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
        return {item: _textualize(item, getattr(self, item)) for item in self.__slots__}

    def _from_dict(self, dictionary: Dict[str, Any]):
        for key, value in dictionary.items():
            if key in self.__slots__:
                setattr(self, key, value)
            else:
                raise AttributeError("Configuration has not attribute '{}'".format(key))

    def _to_yaml(self) -> str:
        """
        Converts the configuration object to a YAML format using the 
        dictionary representation of the object.
        """
        return yaml.dump(self._to_dict(), default_flow_style=False, sort_keys=False)

    def _from_yaml(self, cfg: str):
        """
        Sets the configuration object from a YAML formatted string by 
        converting to a dictionary and updating the object's keys.
        """
        self._from_dict(yaml.load(cfg, Loader=yaml.FullLoader))

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

    def use_file(self, filename: Union[str, Path]):
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
        Save the program configuration to the default file location (which is 
        platform dependent).
        """
        loc = appdirs.user_config_dir / CONFIG_FILENAME
        if not loc.is_file():
            loc.parent.mkdir(parents=True, exist_ok=True)
            loc.touch()
        with open(loc, 'w') as f:
            f.write(self._to_yaml())

    def save_as(self, filename: Union[str, Path]):
        """
        Saves the current program configuration to the a specified file (but 
        does not reference that file for configuration).

        Parameters
        ----------
        filename : str
            The location to save the configuration file to.
        """
        with open(filename, 'w') as f:
            f.write(self._to_yaml())

    def dump(self) -> str:
        """
        Dumps the program configuration to a YAML-formatted string.

        Returns
        -------
        str
            The dumped configuration settings.
        """
        return self._to_yaml()


global_config = Configuration()


def dump():
    print(global_config.dump())


if __name__ == "__main__":
    dump()
