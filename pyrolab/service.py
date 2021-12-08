# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Service
-------

Submodule defining interfaces for PyroLab services.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Type


log = logging.getLogger(__name__)


class Service:
    """
    Abstract base class provides a common interface for services and instruments.
    """
    pass

    @classmethod
    def set_behavior(cls, instancemode: str="session"):
        pass


class ServiceInfo:
    """
    Groups together information about a PyroLab service, including connection
    parameters for ``autoconnect()``.

    Parameters
    ----------
    name : str
        A unique human-readable name for identifying the instrument.
    module : str
        The PyroLab module the class belongs to, as a string.
    classname : str
        The classname of the object to be registered, as a string.
    parameters : Dict[str, Any]
        A dictionary of parameters passed to the object's ``connect()`` 
        function when ``autoconnect()`` is invoked.        
    description : str
        Description string for providing more information about the device.
        Will be displayed in the nameserver.
    instancemode : str, optional
        The mode of the object to be created. See ``Service.set_behavior()``.
        Default is ``session``.
    server : str, optional
        The name of the daemon configuration to register the service with.
        Default is ``default``.
    nameservers : List[str], optional
        A list of nameservers to register the service with. Default is [] (no
        registration).
    """
    def __init__(self, 
                 name: str="", 
                 module: str="", 
                 classname: str="", 
                 parameters: Dict[str, Any]={},
                 description: str="", 
                 instancemode: str="session",
                 server: str="default",
                 nameservers: List[str]=[]) -> None:
        self.name = name
        self.module = module
        self.classname = classname
        self.parameters = parameters
        self.description = description
        self.instancemode = instancemode
        self.server = server
        self.nameservers = nameservers

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.fqn}) at {hex(id(self))}>"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    @property
    def fqn(self) -> str:
        """
        Fully-qualified name, ``<module>.<class>``.

        Returns
        -------
        str
            The fully-qualified name.
        """
        return self.module + "." + self.classname

    # @classmethod
    # def from_dict(cls, dictionary: Dict[str, Any]) -> ServiceInfo:
    #     """
    #     Builds a InstrumentInfo class from a dictionary.

    #     Parameters
    #     ----------
    #     dictionary : Dict[str, Any]
    #         A dictionary of the attributes that can be used to reconstruct the
    #         data class.

    #     Returns
    #     -------
    #     InstrumentInfo
    #         An InstrumentInfo object instantiated from a dictionary.
    #     """
    #     nc = cls(**dictionary)
    #     return nc

    # def to_dict(self) -> Dict[str, Any]:
    #     """
    #     Converts all key-value attributes to a dict. Can be used for persisting
    #     data. The output format can be converted back into an object using
    #     the ``from_dict()`` method.

    #     Returns
    #     -------
    #     Dict[str, Any]
    #         A dictionary of all the public attributes in the data class.
    #     """
    #     return self.__dict__
