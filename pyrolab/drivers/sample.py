# -*- coding: utf-8 -*-
#
# Copyright © Sequoia Ploeg
# Licensed under the terms of the MIT License
# (see pyrolab/__init__.py for details)

"""
Sample Service
--------------

This file implements some simple, sample services for testing whether a server
is working properly.
"""

from typing import Union

import pyrolab.api


Number = Union[int, float]

    
@pyrolab.api.expose
class SampleService:
    def __init__(self):
        pass

    def echo(self, message: str) -> str:
        return "SERVER RECEIVED: " + message

    def add(self, *a) -> Number:
        """
        Adds an unconstrained number of arguments together.
        """
        return sum(a)

    def subtract(self, a: Number, b) -> Number:
        """
        Subtracts the second parameter from the first.
        """
        return a - b

    def multiply(self, *vals) -> Number:
        """
        Multiplies an unconstrained number of arguments together.
        """
        final = 1
        for val in vals:
            final = final * val
        return final

    def divide(self, num: Number, den: Number) -> Number:
        """
        Divides the first argument by the second.
        """
        return num / den
