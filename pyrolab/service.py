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
from typing import Callable, Optional


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
