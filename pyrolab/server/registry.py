# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Server Registry
---------------

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
import atexit
import importlib
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Generator, Set, Type, Union
from pprint import PrettyPrinter
import logging

from yaml import safe_load, dump

from pyrolab.server.configure import SERVER_DATA_DIR
from pyrolab.server.locker import create_lockable

if TYPE_CHECKING:
    from pyrolab.drivers import Instrument


log = logging.getLogger("pyrolab.server.registry")


# TODO: Make this some sort of PyroLab configuration parameter.
REGISTRY_AUTOSAVE = True


class InstrumentInfo:
    """
    Groups together information about a PyroLab driver, including connection
    parameters for ``autoconnect()``.

    Parameters
    ----------
    registered_name : str
        The name used to register the class with a nameserver.
    module : str
        The PyroLab module the class belongs to, as a string.
    class_name : str
        The class name of the object to be registered, as a string.
    connect_params : Dict[str, Any]
        A dictionary of parameters passed to the object's ``connect()`` 
        function when ``autoconnect()`` is invoked.
    lockable : bool
        Whether the class should be made lockable whene instantiated.
    metadata : Set[str]
        Metadata that should be registered with the nameserver. Often is just
        comments or notes to display to the user.
    """
    def __init__(self, registered_name: str="", module: str="", 
                 class_name: str="", connect_params: Dict[str, Any]={},
                 lockable: bool=False, metadata: Set[str]=set()) -> None:
        self.registered_name = registered_name
        self.module = module
        self.class_name = class_name
        self.connect_params = connect_params
        self.lockable = lockable
        self.metadata = metadata

    def __repr__(self) -> str:
        return f"<'{self.registered_name}': {self.__class__.__name__}({self.fqn}) at {hex(id(self))}>"

    @property
    def fqn(self) -> str:
        """
        Fully-qualified name, ``<module>.<class>``.
        """
        return self.module + "." + self.class_name

    @classmethod
    def from_dict(cls, dictionary: Dict[str, Any]) -> InstrumentInfo:
        """
        Builds a InstrumentInfo class from a dictionary.

        Parameters
        ----------
        dictionary : Dict[str, Any]
            A dictionary of the attributes that can be used to reconstruct the
            data class.

        Returns
        -------
        InstrumentInfo
            An InstrumentInfo object instantiated from a dictionary.
        """
        nc = cls(**dictionary)
        return nc

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts all key-value attributes to a dict. Can be used for persisting
        data. The output format can be converted back into an object using
        the ``from_dict()`` method.

        Returns
        -------
        Dict[str, Any]
            A dictionary of all the public attributes in the data class.
        """
        return self.__dict__

    def get_class(self) -> Type[Instrument]:
        """
        Returns the object for the class in PyroLab referenced by 
        InstrumentInfo. If the class is lockable, returns the lockable version.

        Returns
        -------
        Type[Instrument]
            The class of the referenced Instrument.
        """
        mod = importlib.import_module(self.module)
        obj: Instrument = getattr(mod, self.class_name)
        if self.lockable:
            obj = create_lockable(obj)
        return obj


# TODO: Make this some sort of PyroLab configuration parameter.
INSTRUMENT_REGISTY_FILE = SERVER_DATA_DIR / "instrument_registry.yaml"

class InstrumentRegistry:
    """
    Contains a registry of InstrumentInfo objects. 

    PyroLab maintains a reference to a single InstrumentRegistry object, 
    although the class is not implemented as a Singleton. This means that the
    class can be instantiated by external scripts to generate registry files
    that can then be loaded and saved by PyroLab, if desired.

    InstrumentRegistry is iterable; it can be used as:

    ```python
    for instrument in registry:
        # do something
    ```
    """
    def __init__(self) -> None:
        self.instruments: Dict[str, InstrumentInfo] = {}

    def __iter__(self) -> Generator[InstrumentInfo, None, None]:
        yield from self.instruments.values()

    def __len__(self) -> int:
        return len(self.instruments)

    def empty(self) -> None:
        """
        Empties the instrument registry.
        """
        self.instruments = {}

    def get(self, name) -> InstrumentInfo:
        return self.instruments[name]

    def register(self, info: InstrumentInfo):
        """
        Register an InstrumentInfo object. Note that each info's 
        ``registered_name`` must be unique within a registry.

        Parameters
        ----------
        info : InstrumentInfo
            The information object to register.

        Raises
        ------
        Exception
            If the ``registered_name`` already exists in the registry.
        """
        if info.registered_name in self.instruments:
            raise Exception(f"name '{info.registered_name}' already reserved in registry!")
        else:
            self.instruments[info.registered_name] = info

    def unregister(self, name):
        """
        Unregisters a InstrumentInfo from the registry to prevent its being
        persisted.

        Parameters
        ----------
        name : str
            The name the class uses when registering itself with a nameserver.

        Raises
        ------
        Exception
            If the name does not exist in the registry.
        """
        if name not in self.instruments:
            raise Exception(f"name '{name}'' not found in registry!")
        else:
            del self.instruments[name]

    def load(self, path: Union[str, Path]=""):
        """
        Loads InstrumentInfo from a yaml file. Default file is the program's
        internal data file, but a user file can be supplied.

        Parameters
        ----------
        path : Union[str, Path], optional
            The path to the registry file to use. If not provided, uses the
            program's default data file.

        Returns
        -------
            The Registry object is loading is successful, else False.
        """
        if path:
            if type(path) is str:
                path = Path(path)
        else:
            path = INSTRUMENT_REGISTY_FILE
        if path.exists():
            self.empty()
            with path.open('r') as fin:
                infos = safe_load(fin)
                for _, info in infos.items():
                    obj = InstrumentInfo.from_dict(info)
                    self.instruments[obj.registered_name] = obj
            return self
        return False

    def save(self, path: Union[str, Path]="", update_file: bool=False):
        """
        Saves the current registry to file for persisting instruments.

        A path can be specified to create a new file with Instrument 
        information. This is for inspection or development purposes. If
        ``update_file`` is True, PyroLab can reference that file's location
        each time it is started instead of using its default ProgramData file.
        (TODO: this is not yet impmlemented.)

        Parameters
        ----------
        path : Union[str, Path], optional
            The location to save the instrument registry file to.
        update_file : bool, optional
            Force PyroLab to update it's default instrument registry file 
            location. TODO: NotYetImplemented
        """
        if path:
            if type(path) is str:
                path = Path(path)
        else:
            path = INSTRUMENT_REGISTY_FILE
        items = {name: info.to_dict() for name, info in self.instruments.items()}
        with path.open('w') as fout:
            fout.write(dump(items))
        
        if update_file:
            raise NotImplementedError

    def prettyprint(self):
        pp = PrettyPrinter()
        pp.pprint(self.instruments)


registry = InstrumentRegistry()
registry.load()

@atexit.register
def save_registry_on_exit():
    if REGISTRY_AUTOSAVE:
        registry.save()
