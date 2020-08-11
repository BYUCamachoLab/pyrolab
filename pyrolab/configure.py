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

from pyrolab import dirs


class Configuration:
    """
    Available configuration items are shown here.
    
    Warning
    -------
    Do not edit the values directly in this module! They are the global 
    defaults. Instead, provide a valid configuration file to PyroLab.
    """
    __slots__ = [
        "HOST", 
        "NS_HOST", 
        "LOGFILE", 
        "LOGLEVEL", 
        "SSL", 
        "SSL_SERVERCERT",
        "SSL_SERVERKEY",
        "SSL_SERVERKEYPASSWD",
        "SSL_REQUIRECLIENTCERT",
        "SSL_CLIENTCERT",
        "SSL_CLIENTKEY",
        "SSL_CLIENTKEYPASSWD",
    ]

    def __init__(self):
        self.reset()

    def reset(self):
        self.HOST = "localhost"
        self.NS_HOST = "localhost"
        self.LOGFILE = Path.home() / 'PyroLab.log'
        self.LOGLEVEL = "ERROR"
        self.SSL = True
        self.SSL_SERVERCERT = ""
        self.SSL_SERVERKEY = ""
        self.SSL_SERVERKEYPASSWD = ""
        self.SSL_REQUIRECLIENTCERT = False
        self.SSL_CLIENTCERT = ""
        self.SSL_CLIENTKEY = ""
        self.SSL_CLIENTKEYPASSWD = ""

        # cfile = _data_path / 'config.ini'
        # if cfile.is_file():
        #     print("Configuration found!")

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        if hasattr(self, key):
            if type(getattr(self, key)) == type(value):
                setattr(self, key, value)
            else:
                raise TypeError("expected type '{}', got '{}' instead.".format(type(self.__dict__[key]), type(value)))

    # def set_log_level(self, level):
    #     """
    #     Sets the logging level, given a value as a string. 

    #     Parameters
    #     ----------
    #     level : str
    #         One of [NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL]. The input
    #         is not case sensitive, but the full word is required (i.e. 
    #         "warning", not "warn").
    #     """
    #     self.LOGLEVEL = getattr(logging, level.upper())

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

    def as_dict(self):
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
                    raise TypeError
            else:
                raise ValueError

    def _from_ini(self):
        pass

    def _as_ini(self):
        pass

    def open(self, filename):
        pass

    def save(self):
        pass

    def saveas(self, filename):
        pass

    def dump(self):
        pass


global_config = Configuration()


def dump():
    print(global_config.dump())


if __name__ == "__main__":
    dump()