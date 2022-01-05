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

uc480.start_stream()
print("video started")
time.sleep(3)
print("let's get to it")
while(True):
    frame = uc480.get_frame()
    print(f"got frame, {frame.shape}")
    cv2.imshow('UC480',frame)  #paint the image to the cv2 window
    keyCode = cv2.waitKey(30)

    if cv2.getWindowProperty('UC480',cv2.WND_PROP_VISIBLE) < 1:   
        break

uc480.end_stream()
