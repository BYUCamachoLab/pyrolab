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
    def __init__(self) -> None:
        self._autoconnect_params: Dict[str, Any] = {}

    @staticmethod
    def detect_devices() -> List[Dict[str, Any]]:
        raise NotImplementedError

    def connect(self, **kwargs) -> bool:
        """
        Connects to instruments or services that require initialization.

        Returns
        -------
        bool
            True if connection was successful, False otherwise.
        """
        raise NotImplementedError

    @expose
    def autoconnect(self) -> None:
        if not self._autoconnect_params:
            raise Exception("No autoconnection parameters available")
        else:
            return self.connect(**self._autoconnect_params)

    def close(self) -> None:
        raise NotImplementedError
