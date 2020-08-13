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

import pyrolab.api

    
@pyrolab.api.expose
class SampleService:
    def __init__(self):
        pass

    def echo(self, message):
        return "SERVER RECEIVED: " + message

    def add(self, *a):
        """
        Adds an unconstrained number of arguments together.
        """
        return sum(a)

    def subtract(self, a, b):
        """
        Subtracts the second parameter from the first.
        """
        return a - b

    def multiply(self, *vals):
        """
        Multiplies an unconstrained number of arguments together.
        """
        final = 1
        for val in vals:
            final = final * val
        return final

    def divide(self, num, den):
        """
        Divides the first argument by the second.
        """
        return num / den
