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

Server Configuration
====================

Note the difference between the two ``servertypes``:

1. Threaded server
    Every proxy on a client that connects to the daemon will be assigned to a 
    thread to handle the remote method calls. This way multiple calls can 
    potentially be processed concurrently. This means your Pyro object may have 
    to be made thread-safe! 

2. Multiplexed server
    This server uses a connection multiplexer to process all remote method 
    calls sequentially. No threads are used in this server. It means only one 
    method call is running at a time, so if it takes a while to complete, all 
    other calls are waiting for their turn (even when they are from different 
    proxies).


Service Registry
=================

The registry saves previously discovered or registered devices on a local
server machine. 

It maintains a data directory with paths corresponding to different 
nameservers. Instruments are stored in a single text file, by default named
``instrument_registry.yaml``.

The device.instr file specification is a yaml file, a list with the following 
fields:
    name: string for nameserver registration name
    module: string representing the object's module in the pyrolab library
    class_name: string representing the object's class in the pyrolab library
    connect_params: dictionary of key-value pairs, autoconnection parameters 
        for the given instrument.

The registry automatically saves its state every time PyroLab is closed.
This behavior can be altered by setting the flag TODO in PyroLab's 
configuration settings.
"""

from __future__ import annotations
import importlib
import logging
from multiprocessing import Value
import pkg_resources
from pathlib import Path
from pprint import PrettyPrinter
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional, Set, Type, Union

from yaml import safe_load, dump

from pyrolab import PYROLAB_CONFIG_DIR, PYROLAB_DATA_DIR
from pyrolab.nameserver import NameServerConfiguration
from pyrolab.daemon import DaemonConfiguration
from pyrolab.service import Service, ServiceInfo
from pyrolab.utils import generate_random_name

if TYPE_CHECKING:
    from pyrolab.drivers import Instrument


log = logging.getLogger(__name__)


CONFIG_DIR = PYROLAB_CONFIG_DIR / "config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
USER_CONFIG_FILE = CONFIG_DIR / "user_configuration.yaml"


def get_config_file() -> Path:
    """
    Returns the path to the configuration file.

    If a user configuration file exists, it is used. Otherwise, the default
    configuration file is used.

    Returns
    -------
    config_file : Path
        The path to the configuration file.
    """
    if USER_CONFIG_FILE.exists():
        return USER_CONFIG_FILE
    else:
        return Path(pkg_resources.resource_filename('pyrolab', "data/config/default.yaml"))


def update_config(filename: Union[str, Path]=None) -> None:
    """
    Updates the internal configuration file with a user configuration file.

    Parameters
    ----------
    filename : str or Path, optional
        The path to the configuration file. If not provided, the default file
        from PyroLab's persistent data is used.

    Raises
    ------
    FileNotFoundError
        If the configuration file does not exist.
    ValueError
        If a filename is not specified.
    """
    if filename is None:
        raise ValueError("No configuration file provided.")
    filename = Path(filename)
    if not filename.exists():
        raise FileNotFoundError(f"Configuration file '{filename}' not found.")
    with open(filename, "r") as fin:
        with open(USER_CONFIG_FILE, "w") as fout:
            fout.write(fin.read())


def reset_config() -> None:
    """
    Resets the configuration to the default.

    This function deletes the user configuration file, reverting to the default
    configuration each time PyroLab is started.
    """
    USER_CONFIG_FILE.unlink(missing_ok=True)


def load_ns_configs(filename: Union[str, Path]=None) -> Dict[str, NameServerConfiguration]:
    """
    Reads the nameserver configurations from a YAML file. 
    
    If no filename is provided, the default file from PyroLab's persistent
    data is used.

    Parameters
    ----------
    filename : str or Path, optional
        The path to the configuration file. If not provided, the default file
        from PyroLab's persistent data is used.

    Returns
    -------
    ns_configurations: Dict[str, NameserverConfiguration]
        A dictionary of configuration names to NameserverConfiguration objects.

    Examples
    --------
    Suppose we have the following configuration file:

    .. code-block:: yaml
        nameservers:
            - production:
                host: camacholab.ee.byu.edu
                ns_port: 9090
                broadcast: false
                ns_bchost: null
                ns_bcport: 9091
                ns_autoclean: 15.0
                storage_type: sql
            - development:
                host: localhost
                ns_port: 9090

    Note that, regardless of whether it is present in the file, the default
    configuration is always available. It has the following settings:

    .. code-block:: yaml
        nameservers:
            - default:
                host: localhost
                broadcast: false
                ns_port: 9090
                ns_bchost: localhost
                ns_bcport: 9091
                ns_autoclean: 0.0
                storage_type: sql
                storage_filename: <pyrolab default data directory>

    If a profile named "default" exists in the file, the base default is 
    overridden. Many places in PyroLab read the default configuration, so be
    careful and make sure you actually want to change the default.
    
    >>> from pyrolab.configure import load_ns_configs
    >>> nsconfigs = load_ns_configs("config.yaml")
    >>> list(nsconfigs.keys())
    ['default', 'production', 'development']
    """
    if filename is None:
        filename = get_config_file()
    filename = Path(filename)
    if not filename.exists():
        raise FileNotFoundError(f"Configuration file '{filename}' not found.")
    with open(filename, "r") as f:
        config = safe_load(f)
    ns_configurations = {"default": NameServerConfiguration()}
    if "nameservers" in config:
        for ns in config["nameservers"]:
            ns_name, ns_config = list(ns.items())[0]
            ns_configurations[ns_name] = NameServerConfiguration(**ns_config)
        return ns_configurations
    else:
        # raise ValueError(f"Configuration file '{filename}' does not contain a 'nameservers' section.")
        return ns_configurations


def load_server_configs(filename: Union[str, Path]=None) -> Dict[str, DaemonConfiguration]:
    """
    Reads the server configurations from a YAML file. 
    
    If no filename is provided, the default file from PyroLab's persistent
    data is used.

    Parameters
    ----------
    filename : str or Path, optional
        The path to the configuration file. If not provided, the default file
        from PyroLab's persistent data is used.

    Returns
    -------
    s_configurations: Dict[str, NameserverConfiguration]
        A dictionary of configuration names to NameserverConfiguration objects.

    Examples
    --------
    Suppose we have the following configuration file:

    .. code-block:: yaml
        servers:
            - lockable:
                classname: LockableDaemon
                host: public
                servertype: thread
            - multiplexed: 
                host: public
                servertype: multiplex

    Note that, regardless of whether it is present in the file, the default
    configuration is always available. It has the following settings:

    .. code-block:: yaml
        servers:
            - default:
                classname: Daemon
                host: localhost
                servertype: thread

    If a profile named "default" exists in the file, the base default is 
    overridden. Many places in PyroLab read the default configuration, so be
    careful and make sure you actually want to change the default.
    
    >>> from pyrolab.configure import load_server_configs
    >>> sconfigs = load_server_configs("config.yaml")
    >>> list(sconfigs.keys())
    ['default', 'lockable', 'multiplexed']
    """
    if filename is None:
        filename = get_config_file()
    filename = Path(filename)
    if not filename.exists():
        raise FileNotFoundError(f"Configuration file '{filename}' not found.")
    with open(filename, "r") as f:
        config = safe_load(f)
    s_configurations = {"default": DaemonConfiguration()}
    if "servers" in config:
        for listing in config["servers"]:
            s_name, s_config = list(listing.items())[0]
            s_configurations[s_name] = DaemonConfiguration(**s_config)
        return s_configurations
    else:
        # raise ValueError(f"Configuration file '{filename}' does not contain a 'servers' section.")
        return s_configurations


def load_service_configs(filename: Union[str, Path]=None) -> Dict[str, ServiceInfo]:
    """
    Reads the services configurations from a YAML file. 
    
    If no filename is provided, the default file from PyroLab's persistent
    data is used.

    Parameters
    ----------
    filename : str or Path, optional
        The path to the configuration file. If not provided, the default file
        from PyroLab's persistent data is used.

    Returns
    -------
    service_configs: Dict[str, ServiceInfo]
        A dictionary of configuration names to NameserverConfiguration objects.

    Examples
    --------
    Suppose we have the following configuration file:

    .. code-block:: yaml
        services:
            - asgard.wolverine:
                module: pyrolab.drivers.motion.prm1z8
                classname: PRM1Z8
                parameters:
                    - serialno: 27003366
                description: Rotational motion
                instancemode: single
                server: lockable
                nameservers: 
                    - production
            - asgard.hulk:
                module: pyrolab.drivers.motion.z825b
                classname: Z825B
                parameters:
                    - serialno: 27003497
                description: Longitudinal motion
                instancemode: single
                server: lockable
                nameservers: 
                    - production
    
    >>> from pyrolab.configure import load_service_configs
    >>> services = load_service_configs("config.yaml")
    >>> list(services.keys())
    ['asgard.wolverine', 'asgard.hulk']
    """
    if filename is None:
        filename = get_config_file()
    filename = Path(filename)
    if not filename.exists():
        raise FileNotFoundError(f"Configuration file '{filename}' not found.")
    with open(filename, "r") as f:
        config = safe_load(f)
    services = {}
    if "services" in config:
        for listing in config["services"]:
            s_name, s_config = list(listing.items())[0]
            if s_name[:4] == "auto":
                _, count = s_name.split(" ")
                s_name = generate_random_name(count=int(count))
            services[s_name] = ServiceInfo(name=s_name, **s_config)
        return services
    else:
        # raise ValueError(f"Configuration file '{filename}' does not contain a 'services' section.")
        return services


def get_servers_used_by_services(service_cfgs: Dict[str, Any]) -> List[str]:
    """
    Finds all the required servers for a given service configuration.

    Not all servers defined in the configuration file are necessarily used.
    This function finds all the servers that are actually used by the
    defined services.

    Parameters
    ----------
    service_cfgs : Dict[str, Any]
        A dictionary of service configurations, the output of 
        :py:func:`load_service_configs`.

    Returns
    -------
    required_servers : List[str]
        A list of the names of the required servers.

    Examples
    --------
    >>> from pyrolab.configure import load_service_configs, get_required_servers
    >>> services = load_service_configs("config.yaml")
    >>> get_required_servers(services) 
    ['lockable']
    """
    return list(set([v['server'] for v in service_cfgs.values()]))


def get_services_for_server(servername: str, services: Optional[Dict[str, Any]]=None) -> Dict[str, ServiceInfo]:
    """
    Finds all the services that use a given server.

    Parameters
    ----------
    server_name : str
        The name of the server.
    services : Dict[str, Any], optional
        A dictionary of service configurations, the output of
        :py:func:`load_service_configs`. If not provided, the configuration is
        determined by reading the default (or persisted) configuration file.
    
    Returns
    -------
    services : List[Dict[str, Any]]
        A list of service configurations (by name) that use the server.
    """
    if not services:
        services = load_service_configs()
    return {k: v for k, v in services.items() if v['server'] == servername}


def fqn(module, classname) -> str:
    """
    Fully-qualified name, ``<module>.<class>``.

    Parameters
    ----------
    module : str
        The module name.
    classname : str
        The class name.

    Returns
    -------
    str
        The fully-qualified name.
    """
    return module + "." + classname


# def get_class(self) -> Type[Service]:
#     """
#     Returns the object for the class in PyroLab referenced by 
#     InstrumentInfo. If the class is lockable, returns the lockable version.

#     Returns
#     -------
#     Type[Instrument]
#         The class of the referenced Instrument.
#     """
#     mod = importlib.import_module(self.module)
#     obj: Service = getattr(mod, self.classname)
#     if self.server == "LockableDaemon":
#         obj = create_lockable(obj)
#     return obj


# class ServiceRegistry:
#     """
#     Contains a registry of InstrumentInfo objects. 

#     PyroLab maintains a reference to a single InstrumentRegistry object, 
#     although the class is not implemented as a Singleton. This means that the
#     class can be instantiated by external scripts to generate registry files
#     that can then be loaded and saved by PyroLab, if desired.

#     InstrumentRegistry is iterable; it can be used as:

#     ```python
#     for instrument in registry:
#         # do something
#     ```
#     """
#     def __init__(self) -> None:
#         self.instruments: Dict[str, InstrumentInfo] = {}

#     def __iter__(self) -> Generator[InstrumentInfo, None, None]:
#         yield from self.instruments.values()

#     def __len__(self) -> int:
#         return len(self.instruments)

#     def empty(self) -> None:
#         """
#         Empties the instrument registry.
#         """
#         self.instruments = {}

#     def get(self, name: str) -> InstrumentInfo:
#         """
#         Gets an InstrumentInfo object by name.

#         Parameters
#         ----------
#         name : str
#             The name of the InstrumentInfo to get.

#         Returns
#         -------
#         info : InstrumentInfo
#             The info object in the registry with the given name.
#         """
#         return self.instruments[name]

#     def register(self, info: InstrumentInfo):
#         """
#         Register an InstrumentInfo object. Note that each info's 
#         ``registered_name`` must be unique within a registry.

#         Parameters
#         ----------
#         info : InstrumentInfo
#             The information object to register.

#         Raises
#         ------
#         Exception
#             If the ``registered_name`` already exists in the registry.
#         """
#         if info.name in self.instruments:
#             raise Exception(f"name '{info.name}' already reserved in registry!")
#         else:
#             self.instruments[info.name] = info

#     def unregister(self, name):
#         """
#         Unregisters a InstrumentInfo from the registry to prevent its being
#         persisted.

#         Parameters
#         ----------
#         name : str
#             The name the class uses when registering itself with a nameserver.

#         Raises
#         ------
#         Exception
#             If the name does not exist in the registry.
#         """
#         if name not in self.instruments:
#             raise Exception(f"name '{name}'' not found in registry!")
#         else:
#             del self.instruments[name]

#     def load(self, path: Union[str, Path]=""):
#         """
#         Loads InstrumentInfo from a yaml file. Default file is the program's
#         internal data file, but a user file can be supplied.

#         Parameters
#         ----------
#         path : Union[str, Path], optional
#             The path to the registry file to use. If not provided, uses the
#             program's default data file.

#         Returns
#         -------
#             The Registry object is loading is successful, else False.
#         """
#         if path:
#             if type(path) is str:
#                 path = Path(path)
#         else:
#             path = INSTRUMENT_REGISTY_FILE
#         if path.exists():
#             self.empty()
#             with path.open('r') as fin:
#                 infos = safe_load(fin)
#                 for _, info in infos.items():
#                     obj = InstrumentInfo.from_dict(info)
#                     self.instruments[obj.name] = obj
#             return self
#         return False

#     def save(self, path: Union[str, Path]="", update_file: bool=False):
#         """
#         Saves the current registry to file for persisting instruments.

#         A path can be specified to create a new file with Instrument 
#         information. This is for inspection or development purposes. If
#         ``update_file`` is True, PyroLab can reference that file's location
#         each time it is started instead of using its default ProgramData file.
#         (TODO: this is not yet impmlemented.)

#         Parameters
#         ----------
#         path : Union[str, Path], optional
#             The location to save the instrument registry file to.
#         update_file : bool, optional
#             Force PyroLab to update it's default instrument registry file 
#             location. TODO: NotYetImplemented
#         """
#         if path:
#             if type(path) is str:
#                 path = Path(path)
#         else:
#             path = INSTRUMENT_REGISTY_FILE
#         items = {name: info.to_dict() for name, info in self.instruments.items()}
#         with path.open('w') as fout:
#             fout.write(dump(items))
        
#         if update_file:
#             raise NotImplementedError

#     def prettyprint(self) -> None:
#         """
#         Utility for pretty printing the instruments contained within the 
#         registry.
#         """
#         pp = PrettyPrinter()
#         pp.pprint(self.instruments)


# import uuid
# def create_unique_resource(cls, **kwargs) -> Instrument:
#     """
#     Dynamically create a new class that is subclassed from ``cls``. Adds 
#     attributes to the class as key-value pairs from ``**kwargs``.

#     Parameters
#     ----------
#     cls : class
#         The class to be used as a template while dynamically creating a new
#         class.
#     **kwargs
#         Any number of key-value pairs to be added as attribtes to the class.
    
#     Returns
#     -------
#     class
#         A subclass that inherits from the original class.
#     """
#     class_id = uuid.uuid4().hex
#     kwargs["id"] = class_id
#     UniqueResource = type(
#         cls.__name__ + "_" + class_id,
#         (cls, ),
#         kwargs,
#     )
#     return UniqueResource
