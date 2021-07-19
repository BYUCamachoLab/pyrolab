# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Drivers
-------

Submodule containing drivers for each supported instrument type.
"""

import logging

from pyrolab.server import expose
from typing import Any, Dict, List


log = logging.getLogger('pyrolab.drivers')


class Instrument:
    """
    Abstract base class Instrument provides a common interface for other
    PyroLab features.
    """
    def __init__(self) -> None:
        if not hasattr(self, "_autoconnect_params"):
            self._autoconnect_params: Dict[str, Any] = {}

    def __del__(self) -> None:
        """
        Destructor. Automatically calls ``close()`` to release any potentially
        claimed resources.
        """
        self.close()

    @staticmethod
    def detect_devices() -> List[Dict[str, Any]]:
        """
        Returns a list of dictionaries that could be passed directly to 
        connect. Each list item is a 

        Returns
        -------
        List[Dict[str, Any]]
            Each list item represents a unique device. The dictionary is the
            keyword arguments passed to ``connect()``. If devices cannot be
            detected, this should return an empty list.
        """
        raise NotImplementedError

    def connect(self, **kwargs) -> bool:
        """
        Connects to instruments or services that require initialization. All
        parameters must be keyword arguments; the presence of any position
        arguments will break the functionality of ``autoconnect()``.

        Returns
        -------
        bool
            True if connection was successful, False otherwise.
        """
        raise NotImplementedError

    @expose
    def autoconnect(self) -> None:
        """
        If the device is persisted in PyroLab's program data, the parameters
        for connect should be saved. ``autoconnect()`` simply calls 
        ``connect()`` with the saved parameters.

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
        Releases resources, hardware or otherwise. Deletion of object should 
        also automatically call ``close()``, which should take no parameters.

        Raises
        ------
        NotImplementedError
            If not overridden; should return None otherwise.
        """
        raise NotImplementedError
