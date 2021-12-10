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
from typing import Any, Dict, List, Set, Type, Optional, Callable, Union
from pyrolab.utils import generate_random_name

from pyrolab.utils.configure import Configuration


log = logging.getLogger(__name__)


class Service:
    """
    Abstract base class provides a common interface for services and instruments.
    """
    @classmethod
    def set_behavior(cls, instance_mode: str="session", instance_creator: Optional[Callable]=None) -> None:
        """
        Sets the Pyro5 behavior for the class (modified in place).
        
        Equivalent to using the ``behavior`` decorator on the class, but can 
        be used dynamically during runtime. Services that specify some default
        behavior in the source code can be overridden using this function.

        Parameters
        ----------
        instance_mode : str
            One of "session", "single", or "percall" (see manual for differences).
        instance_creator : callable
            A callable that creates a new instance of the class (see manual for
            more details).

        Raises
        ------
        ValueError
            If ``instance_mode`` is not one of "session", "single", or "percall".
        TypeError
            If ``instance_mode`` is not a string or ``instance_creator`` is 
            defined but is not callable.
        """
        if not isinstance(instance_mode, str):
            raise TypeError(f"instance_mode must be a string, but is {type(instance_mode)}")
        if instance_mode not in ("single", "session", "percall"):
            raise ValueError(f"invalid instance mode: {instance_mode}")
        if instance_creator and not callable(instance_creator):
            raise TypeError("instance_creator must be a callable")
        cls._pyroInstancing = (instance_mode, instance_creator)


class ServiceConfiguration(Configuration):
    """
    Groups together information about a PyroLab service. 
    
    Includes connection parameters for ``autoconnect()``. Services defined in
    other modules or libaries can also be included here, so long as the module
    can be found by the Python environment.

    Parameters
    ----------
    name : str
        A unique human-readable name for identifying the instrument. If you're
        not creative, you can use :py:func:`pyrolab.utils.generate_random_name`
        to generate a random name.
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
    kwargs : dict, optional
        These arguments are ignored. They are only here to allow for
        compatibility with the ``Configuration`` class when reinstantiating
        from dictionary.
    """
    def __init__(self, 
                 name: str="", 
                 module: str="", 
                 classname: str="", 
                 parameters: Dict[str, Any]={},
                 description: Union[str, Set[str]]="", 
                 instancemode: str="session",
                 daemon: str="default",
                 nameservers: List[str]=[],
                 **kwargs) -> None:
        super().__init__()
        self.name = name
        self.module = module
        self.classname = classname
        self.parameters = parameters
        if type(description) is not set:
            description = {description}
        self.description = description
        self.instancemode = instancemode
        self.daemon = daemon
        self.nameservers = nameservers

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.fqn}) at {hex(id(self))}>"

    def __str__(self) -> str:
        return f"{self.name} ({self.fqn})"

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
    # def from_dict(cls, dictionary: Dict[str, Any]) -> ServiceConfiguration:
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
