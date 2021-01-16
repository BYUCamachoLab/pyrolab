# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
-----------------------------------------------
Driver for the Arduino that is connected to a Thorlabs Microscope Lamp.
Author: David Hill (https://github.com/hillda3141)
Repo: https://github.com/BYUCamachoLab/pyrolab/blob/bpc303/pyrolab/drivers/motion
"""

from win32event import CreateMutex
from win32api import GetLastError
from winerror import ERROR_ALREADY_EXISTS
from sys import exit

handle = CreateMutex(None, 1, 'ARD_LAMP')

import pyfirmata
import time

if GetLastError() == ERROR_ALREADY_EXISTS:
    # Take appropriate action, as this is the second instance of this script.
    print('An instance of this application is already running.')
    exit(1)

from Pyro5.api import expose, locate_ns, Daemon, config, behavior

def get_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

import pyrolab.api

@expose
class ARD_LAMP:

    def __init__(self, port="COM5"):
        pass

    def set_port(self,port='COM5'):
        self.port = port

    def start_serial(self):
        self.board = pyfirmata.Arduino(self.port)

    def on(self,pin=13):
        self.board.digital[pin].write(1)

    def off(self,pin=13):
        self.board.digital[pin].write(0)

    def end(self):
        for x in range(2,13):
            self.board.digital[x].write(0)


if __name__ == "__main__":
    config.HOST = get_ip()
    config.SERVERTYPE = "multiplex"
    daemon = Daemon()
    ns = locate_ns(host="camacholab.ee.byu.edu")

    uri = daemon.register(ARD_LAMP)
    ns.register("ARD_LAMP", uri)
    try:
        daemon.requestLoop()
    finally:
        ns.remove("ARD_LAMP")