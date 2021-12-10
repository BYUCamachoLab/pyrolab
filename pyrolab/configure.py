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
import logging
import warnings
import pkg_resources
from pathlib import Path
from multiprocessing.process import current_process
from typing import Dict, List, Tuple, Union

from yaml import safe_load, dump

from pyrolab import PYROLAB_CONFIG_DIR, PYROLAB_DATA_DIR
from pyrolab.nameserver import NameServerConfiguration
from pyrolab.daemon import DaemonConfiguration
from pyrolab.service import ServiceConfiguration
from pyrolab.utils import generate_random_name
from pyrolab.utils.network import get_ip


log = logging.getLogger(__name__)


CONFIG_DIR = PYROLAB_CONFIG_DIR / "config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

ACTIVE_DATA_DIR = PYROLAB_DATA_DIR / "activedata"
ACTIVE_DATA_DIR.mkdir(parents=True, exist_ok=True)

USER_CONFIG_FILE = CONFIG_DIR / "user_configuration.yaml"


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


def validate_name(name) -> Tuple[str, bool]:
    """
    Validates or automatically generates a name. 
    
    If name is "auto n", where n is an integer, it will be replaced with a 
    random name composed of n hyphenated words.

    Parameters
    ----------
    name : str
        The name to validate.

    Returns
    -------
    name : str
        The validated name, or a random name if the name is "auto n".
    is_auto : bool
        Whether the name was automatically generated.

    Raises
    ------
    ValueError
        If the name is set to "auto n" but the string is not properly formatted.
    """
    if name[:5] == "auto ":
        try:
            _, count = name.split(" ")
        except ValueError:
            raise ValueError(f"Invalid name '{name}', must be formatted as 'auto <n>'")
        return generate_random_name(count=int(count)), True
    else:
        return name, False


def read_nameserver_configs(filename: Union[str, Path]) -> List[Tuple[str, NameServerConfiguration]]:
    """
    Reads the nameserver configurations from a YAML file. 

    Parameters
    ----------
    filename : str or Path
        The path to the configuration file.

    Returns
    -------
    nscfgs: List[Tuple[str, DaemonConfiguration]]
        A list of tuples, each being the configuration name with its 
        corresponding :py:class:`NameserverConfiguration` object.

    Examples
    --------
    Here's a possible configuration file. Keys not defined assume the default
    values (see the :py:class:`NameServerConfiguration` class).

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
    
    >>> from pyrolab.configure import read_nameserver_configs
    >>> nsconfigs = read_nameserver_configs("config.yaml")
    >>> [cfg[0] for cfg in nsconfigs]
    ['default', 'production', 'development']
    """
    filename = Path(filename)
    if not filename.exists():
        raise FileNotFoundError(f"Configuration file '{filename}' not found.")
    with open(filename, "r") as f:
        config = safe_load(f)
    nscfgs = []
    if config:
        if "nameservers" in config:
            for ns in config["nameservers"]:
                name, config = list(ns.items())[0]
                nscfgs.append((name, NameServerConfiguration(**config)))
    return nscfgs


def _revert_ipaddress_to_keyword(config: dict) -> None:
    for ipattr in ["host", "ns_host", "ns_bchost"]:
        if config.get(ipattr, None) == get_ip():
            config[ipattr] = "public"


def nameserver_configs_to_yaml(nscfgs: Dict[str, NameServerConfiguration]) -> str:
    """
    Writes the nameserver configurations to a YAML file. 

    Parameters
    ----------
    nscfgs : Dict[str, NameServerConfiguration]
        A dictionary of configuration names to their corresponding 
        :py:class:`NameserverConfiguration` objects.
    """
    config = {"nameservers": []}
    for name, nscfg in nscfgs.items():
        config["nameservers"].append({name: nscfg.to_dict()})
        _revert_ipaddress_to_keyword(config["nameservers"][-1][name])
    return dump(config, default_flow_style=False)


def read_daemon_configs(filename: Union[str, Path]) -> List[Tuple[str, DaemonConfiguration]]:
    """
    Reads the daemon configurations from a YAML file.

    Parameters
    ----------
    filename : str or Path
        The path to the configuration file.

    Returns
    -------
    dcfgs: List[Tuple[str, DaemonConfiguration]]
        A list of tuples, each being the configuration name with its 
        corresponding :py:class:`DaemonConfiguration` object.

    Examples
    --------
    Suppose we have the following configuration file:

    .. code-block:: yaml
        daemons:
            - lockable:
                classname: LockableDaemon
                host: public
                servertype: thread
            - multiplexed: 
                host: public
                servertype: multiplex

    We could then read it like this:
    
    >>> from pyrolab.configure import read_daemon_configs
    >>> dconfigs = read_daemon_configs("config.yaml")
    >>> [daemon[0] for daemon in dconfigs]
    ['lockable', 'multiplexed']
    """
    filename = Path(filename)
    if not filename.exists():
        raise FileNotFoundError(f"Configuration file '{filename}' not found.")
    with open(filename, "r") as f:
        config = safe_load(f)
    dcfgs = []
    if config:
        if "daemons" in config:
            for daemon in config["daemons"]:
                name, config = list(daemon.items())[0]
                # dcfgs[name] = DaemonConfiguration(**config)
                dcfgs.append((name, DaemonConfiguration(**config)))
    return dcfgs


def daemon_configs_to_yaml(dcfgs: Dict[str, DaemonConfiguration]) -> str:
    """
    Writes the daemon configurations to a YAML file.

    Parameters
    ----------
    dcfgs : Dict[str, DaemonConfiguration]
        A dictionary of configuration names to their corresponding 
        :py:class:`DaemonConfiguration` objects.
    """
    config = {"daemons": []}
    for name, dcfg in dcfgs.items():
        config["daemons"].append({name: dcfg.to_dict()})
        _revert_ipaddress_to_keyword(config["daemons"][-1][name])
    return dump(config, default_flow_style=False)


def read_service_configs(filename: Union[str, Path]) -> List[Tuple[str, ServiceConfiguration]]:
    """
    Reads the services configurations from a YAML file. 

    Parameters
    ----------
    filename : str or Path
        The path to the configuration file.

    Returns
    -------
    scfgs: List[Tuple[str, ServiceConfiguration]]
        A list of tuples, each being the configuration names with its
        corresponding :py:class:`ServiceConfiguration` object.

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

    We could then read it like this:
    
    >>> from pyrolab.configure import read_service_configs
    >>> services = read_service_configs("config.yaml")
    >>> [service[0] for service in services]
    ['asgard.wolverine', 'asgard.hulk']
    """
    filename = Path(filename)
    if not filename.exists():
        raise FileNotFoundError(f"Configuration file '{filename}' not found.")
    with open(filename, "r") as f:
        config = safe_load(f)
    scfgs = []
    if config:
        if "services" in config:
            for listing in config["services"]:
                name, config = list(listing.items())[0]
                scfgs.append((name, ServiceConfiguration(**config)))
    return scfgs


def service_configs_to_yaml(scfgs: Dict[str, ServiceConfiguration]) -> str:
    """
    Writes the service configurations to a YAML file.

    Parameters
    ----------
    scfgs : Dict[str, ServiceConfiguration]
        A dictionary of configuration names to their corresponding 
        :py:class:`ServiceConfiguration` objects.
    """
    config = {"services": []}
    for name, scfg in scfgs.items():
        config["services"].append({name: scfg.to_dict()})
    return dump(config, default_flow_style=False)


# def get_servers_used_by_services(service_cfgs: Dict[str, Any]) -> List[str]:
#     """
#     Finds all the required servers for a given service configuration.

#     Not all servers defined in the configuration file are necessarily used.
#     This function finds all the servers that are actually used by the
#     defined services.

#     Parameters
#     ----------
#     service_cfgs : Dict[str, Any]
#         A dictionary of service configurations, the output of 
#         :py:func:`read_service_configs`.

#     Returns
#     -------
#     required_servers : List[str]
#         A list of the names of the required servers.

#     Examples
#     --------
#     >>> from pyrolab.configure import read_service_configs, get_required_servers
#     >>> services = read_service_configs("config.yaml")
#     >>> get_required_servers(services) 
#     ['lockable']
#     """
#     return list(set([v['daemon'] for v in service_cfgs.values()]))


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


ACTIVE_DATA_FILE = CONFIG_DIR / "locked_configurations.yaml"


class GlobalConfiguration:
    """
    A Singleton global configuration object that can read and write configuration files.

    PyroLab configurations are stored in a YAML file. This class provides a
    singleton object that can be used to read and write the configuration file.
    The YAML files contain three sections: ``nameservers``, ``daemons``, and
    ``services``. See the documentation for examples of valid YAML files.

    The user configuration file is stored in 
    ``pyrolab.configure.USER_CONFIG_FILE``. PyroLab instances maintain the 
    configuration state of the file when the program was launched; in other 
    words, if the file is updated, the configuration state of running instances 
    is not modified by default. There are features and switches to turn on
    autoreload, however; see the documentation.

    To ensure all processes have access to the same configuration, the 
    configuration of an active instance is locked to a single file separate 
    from where user-defined configuration files are stored. This class is a 
    singleton; only the main process can modify the configuration. All spawned 
    child processes will use the configuration from the locked file.

    Attributes
    ----------
    nameservers : Dict[str, NameserverConfiguration]
        A dictionary of nameserver configurations.
    daemons : Dict[str, DaemonConfiguration]
        A dictionary of daemon configurations.
    services : Dict[str, ServiceConfiguration]
        A dictionary of service configurations.
    """
    _instance = None

    def __init__(self) -> None:
        raise RuntimeError("Cannot directly instantiate singleton, call ``instance()`` instead.")

    @classmethod
    def instance(cls) -> "GlobalConfiguration":
        """
        Returns the singleton instance of the GlobalConfiguration class.

        Returns
        -------
        GlobalConfiguration
            The singleton instance of the GlobalConfiguration class.
        """
        if cls._instance is None:
            inst = cls.__new__(cls)
            inst.nameservers = {}
            inst.daemons = {}
            inst.services = {}
            inst.features = {}
            cls._instance = inst
        return cls._instance

    def get_config_file(self) -> Path:
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

    def validate(self, filename: Union[str, Path]) -> bool:
        """
        Validates the configuration.

        Checks the following items:
        * Nameservers are defined.
        * Daemons are defined.
        * Services are defined.
        * Nameserver and daemon names are unique.

        Returns
        -------
        bool
            ``True`` if the configuration is valid, ``False`` otherwise.
        """
        return True

    def default_load(self) -> None:
        """
        Reads the default configuration file.

        This method reads the default configuration file and updates the
        configuration object.
        """
        self.load_config_file(self.get_config_file())

    def clear_all(self) -> None:
        """
        Clears all configuration data without reloading built-in defaults.
        """
        self.nameservers = {}
        self.daemons = {}
        self.services = {}
        self.features = {}

    def load_config_file(self, filename: Union[str, Path]) -> None:
        """
        Reads the configuration file and updates the internal configuration.

        Parameters
        ----------
        filename : str or Path
            The path to the configuration file.
        """
        if current_process().name != 'MainProcess':
            raise Exception("GlobalConfiguration should only be dynamically loaded by the main process.")
        for name, config in read_nameserver_configs(filename):
            if not self.add_nameserver(name, config):
                warnings.warn(f"Nameserver '{name}' already exists, cannot be added.")
        for name, config in read_daemon_configs(filename):
            if not self.add_daemon(name, config):
                warnings.warn(f"Daemon '{name}' already exists, cannot be added.")
        for name, config in read_service_configs(filename):
            if not self.add_service(name, config):
                warnings.warn(f"Service '{name}' already exists, cannot be added.")

    def persist(self):
        """
        Persists the configuration to the locked configuration file.

        This method writes the current configuration to the locked configuration
        file.
        """
        pass

    def add_nameserver(self, name: str, config: NameServerConfiguration) -> bool:
        """
        Adds a nameserver to the configuration.

        If an existing nameserver with the same name is found, it is not added.
        The return status indicates whether the nameserver was added 
        sucessfully.

        Parameters
        ----------
        name : str
            The name of the nameserver.
        config : NameserverConfiguration
            The nameserver configuration.

        Returns
        -------
        bool
            ``True`` if the nameserver was added, ``False`` otherwise.
        """
        validname, isauto = validate_name(name)
        if validname in self.nameservers and not isauto:
            return False

        if validname in self.nameservers and isauto:
            while validname in self.nameservers:
                validname, _ = validate_name(name)

        self.nameservers[validname] = config
        return True

    def list_nameservers(self) -> List[str]:
        """
        Lists available nameserver configurations.
        """
        return [k for k in self.nameservers]

    def get_nameserver_config(self, nameserver: str) -> NameServerConfiguration:
        """
        Returns a nameserver configuration by name.

        Parameters
        ----------
        name : str
            The name of the nameserver configuration.

        Returns
        -------
        NameServerConfiguration
            The nameserver configuration.
        """
        return self.nameservers[nameserver]

    def add_daemon(self, name: str, config: DaemonConfiguration) -> bool:
        """
        Adds a daemon to the configuration.

        If an existing daemon with the same name is found, it is not added.
        The return status indicates whether the daemon was added sucessfully.

        Parameters
        ----------
        name : str
            The name of the daemon.
        config : DaemonConfiguration
            The daemon configuration.

        Returns
        -------
        bool
            ``True`` if the daemon was added, ``False`` otherwise.
        """
        validname, isauto = validate_name(name)
        if validname in self.daemons and not isauto:
            return False

        if validname in self.daemons and isauto:
            while validname in self.daemons:
                validname, _ = validate_name(name)

        self.daemons[validname] = config
        return True

    def list_daemons(self) -> List[str]:
        """
        Lists available daemon configurations.
        """
        return [k for k in self.daemons]

    def get_daemon_config(self, daemon: str) -> DaemonConfiguration:
        """
        Returns a daemon configuration by name.

        Parameters
        ----------
        daemon : str
            The name of the daemon configuration.

        Returns
        -------
        DaemonConfiguration
            The daemon configuration.
        """
        return self.daemons[daemon]

    def add_service(self, name: str, config: ServiceConfiguration) -> bool:
        """
        Adds a service to the configuration.

        If an existing service with the same name is found, it is not added.
        The return status indicates whether the service was added sucessfully.

        Parameters
        ----------
        name : str
            The name of the service.
        config : ServiceConfiguration
            The service configuration.

        Returns
        -------
        bool
            ``True`` if the service was added, ``False`` otherwise.
        """
        validname, isauto = validate_name(name)
        if validname in self.services and not isauto:
            return False

        if validname in self.services and isauto:
            while validname in self.services:
                validname, _ = validate_name(name)

        self.services[validname] = config
        return True

    def list_services(self) -> List[str]:
        """
        Lists available service configurations.
        """
        return [k for k in self.services]
        
    def get_service_config(self, service: str) -> ServiceConfiguration:
        """
        Returns a service configuration by name.

        Parameters
        ----------
        service : str
            The name of the service configuration.

        Returns
        -------
        ServiceConfiguration
            The service configuration.
        """
        return self.services[service]

    def list_services_for_daemon(self, daemon: str) -> List[str]:
        """
        Lists services for a daemon.

        Parameters
        ----------
        daemon : str
            The name of the daemon.

        Returns
        -------
        List[str]
            The list of services.
        """
        return [k for k, v in self.services.items() if v.daemon == daemon]

    def get_service_configs_for_daemon(self, daemon: str) -> Dict[str, ServiceConfiguration]:
        """
        Finds all the services that use a given server.

        Parameters
        ----------
        server_name : str
            The name of the server.
        services : Dict[str, Any], optional
            A dictionary of service configurations, the output of
            :py:func:`read_service_configs`. If not provided, the configuration is
            determined by reading the default (or persisted) configuration file.
        
        Returns
        -------
        services : List[Dict[str, Any]]
            A list of service configurations (by name) that use the server.
        """
        return {k: v for k, v in self.services.items() if v['daemon'] == daemon}

    def to_yaml(self) -> str:
        """
        Returns the configuration as a YAML string.
        """
        nscfg = nameserver_configs_to_yaml(self.nameservers)
        dcfg = daemon_configs_to_yaml(self.daemons)
        scfg = service_configs_to_yaml(self.services)
        # TODO: Include options
        return f"{nscfg}\n{dcfg}\n{scfg}"



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
