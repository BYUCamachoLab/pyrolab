import time

from pyrolab.drivers.cameras.thorcam import ThorCamClient

from pyrolab.api import NameServerConfiguration
import numpy as np
import cv2

nscfg = NameServerConfiguration(host="camacholab.ee.byu.edu")
nscfg.update_pyro_config()

uc480 = ThorCamClient()
print("connecting")
uc480.connect("asgard.rocket")
print("connected")
# uc480.color = False

uc480.start_stream()
time.sleep(3)
print("Opening window...")
while(True):
    frame = uc480.get_frame()
    cv2.imshow('UC480', frame)
    keyCode = cv2.waitKey(30)

    if cv2.getWindowProperty('UC480',cv2.WND_PROP_VISIBLE) < 1:   
        break

uc480.end_stream()
