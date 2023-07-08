# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
UC480 Example
=============

This example demonstrates the use of the Thorlabs UC480 camera using PyroLab's
built-in camera client. This uses Pyro5 to negotiate the opening up of a 
socketserver connection with the server. Images are streamed outside of the
PyroLab connection for higher performance. In this example, image are simply
dipslayed in a opencv window.

You may need to install opencv:

    pip install opencv-python
"""

import time

import cv2

from pyrolab.drivers.cameras.thorcam import ThorCamClient
from pyrolab.api import NameServerConfiguration


nscfg = NameServerConfiguration(host="yourdomain.com")
nscfg.update_pyro_config()

uc480 = ThorCamClient()
uc480.connect("CameraPyroName")

uc480.start_stream()
uc480.await_stream()
time.sleep(3)

while True:
    frame = uc480.get_frame()
    cv2.imshow("UC480", frame)
    keyCode = cv2.waitKey(30)

    if cv2.getWindowProperty("UC480", cv2.WND_PROP_VISIBLE) < 1:
        break

uc480.end_stream()
uc480.close()
