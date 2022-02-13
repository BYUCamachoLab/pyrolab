# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Drivers
=======

Submodule containing drivers for each supported instrument type.
"""

import logging
from typing import Any, Dict, List

from pyrolab.api import expose
from pyrolab.service import Service

log = logging.getLogger(__name__)


class Instrument(Service):
    """
    Abstract base class provides a common interface for services and instruments.

    While not a true abstract base class (it *can* be instantiated), all the
    essential functions raise NotImplementedErrors when run. They are therefore
    required to be overridden by derived classes.

    Note that, in order to support autoconnect within the PyroLab framework,
    the ``__init__`` method is never used to set up or connect to the 
    instrument. This is because when objects are hosted by a PyroLab server,
    they are instantiated and that object exists in perpetuity. Since we'd like
    to be able to connect and disconnect from devices while leaving the server
    running (an example use case would be to use the device locally, in a lab,
    manipulating physical controls, without killing the server connection), 
    separate methods ``connect()`` and ``close()`` are required. In this way,
    instruments can be forcibly disconnected without leaving the hosting
    object in an unrecoverable state.

    Attributes
    ----------
    _autoconnect_params : dict
        A private dictionary of parameters that will be used to connect to the
        instrument when hosted by a PyroLab server. This value should never be
        manipulated by a user. It is listed here to prevent accidental
        overwriting by an unwitting user wanting to use the same name.
    """
    def __init__(self) -> None:
        if not hasattr(self, "_autoconnect_params"):
            self._autoconnect_params: Dict[str, Any] = {}

    def __del__(self) -> None:
        """
        Destructor. Automatically calls ``close()``. 
        
        Automatically releases any potentially claimed resources.

        # TODO: This function is unsafe! It is not guaranteed to be called!
        # Enforce calling close() explicitly.
        """
        log.info("Destructing %s", self.__class__.__name__)
        self.close()

    @staticmethod
    def detect_devices() -> List[Dict[str, Any]]:
        """
        Returns a list of connection parameters for available devices.
        
        Static function that can be called without object instantiation.
        Returns all available devices that can be detected on the local
        computer. Each available devices is represented by a dictionary that 
        could be passed directly to :py:func:`connect` using dictionary 
        unpacking.

        Returns
        -------
        List[Dict[str, Any]]
            Each list item represents a unique device. The dictionary is the
            keyword arguments passed to ``connect()``. If devices cannot be
            detected, this should return an empty list.

        Examples
        --------
        >>> available = Instrument.detect_devices()
        >>> device = Instrument()
        >>> device.connect(**available[0])
        """
        raise NotImplementedError

    def connect(self, **kwargs) -> bool:
        """
        Connects to instruments or services that require initialization. 
        
        All parameters must be keyword arguments; the presence of any 
        positional arguments will break the functionality of ``autoconnect()``.

        The base class implements parameters as a keyword argument dictionary.
        Derived classes may declare explicit parameter lists, but all 
        arguments are required to be keyword arguments, i.e. parameters 
        with default values. Default values do not necessarily need to be
        sensible; for example, a default value of None for some required
        parameter. The code should then raise a ValueError for missing
        parameters. The dictionary construct must be used because the 
        autoconnect functionality delivers values to this function as an 
        unpacked dictionary.

        Parameters
        ----------
        kwargs : dict
            A dictionary of parameters required for connection and setup.

        Returns
        -------
        bool
            True if connection was successful, False otherwise.

        Raises
        ------
        NotImplementedError
            If the derived class does not implement this method.
        """
        raise NotImplementedError

    @expose
    def autoconnect(self) -> bool:
        """
        Autoconnect to an instrument using internally stored parameters.

        If the device is persisted in PyroLab's program data, the parameters
        for connect should be saved and associated with the object (in the 
        attribute :py:attr:`_autoconnect_params`). ``autoconnect()`` 
        simply calls :py:func:`connect` with the saved parameters.

        Returns
        -------
        bool
            True if connection was successful, False otherwise.

        Raises
        ------
        Exception
            If the autoconnect parameters are missing.
        """
        if not self._autoconnect_params:
            raise Exception("No autoconnection parameters available")
        else:
            return self.connect(**self._autoconnect_params)

    def close(self) -> None:
        """
        Releases resources, hardware or otherwise. 
        
        Deletion of object should also automatically call ``close()``, which 
        should take no parameters.

        Raises
        ------
        NotImplementedError
            If not overridden; should return None otherwise.
        """
        raise NotImplementedError
