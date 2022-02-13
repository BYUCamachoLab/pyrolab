# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Kinesis Exceptions
==================

Exceptions for the Kinesis driver.
"""

class KinesisError(Exception):
    def __init__(self, *args: object, errcode=0) -> None:
        super().__init__(*args)
        self.errcode = errcode

class KinesisCommunicationError(KinesisError):
    def __init__(self, *args: object, errcode=0) -> None:
        super().__init__(*args, errcode=errcode)

class KinesisDLLError(KinesisError):
    def __init__(self, *args: object, errcode=0) -> None:
        super().__init__(*args, errcode=errcode)

class KinesisMotorError(KinesisError):
    def __init__(self, *args: object, errcode=0) -> None:
        super().__init__(*args, errcode=errcode)
        