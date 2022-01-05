import time

from pyrolab.drivers.cameras.uc480 import UC480Client

from pyrolab.api import NameServerConfiguration
import numpy as np
import cv2

nscfg = NameServerConfiguration(host="camacholab.ee.byu.edu")
nscfg.update_pyro_config()

uc480 = UC480Client()
uc480.connect("asgard.rocket")

uc480.start_video()
time.sleep(3)
while(True):
    cv2.imshow('UC480',uc480.get_frame())  #paint the image to the cv2 window
    keyCode = cv2.waitKey(30)

    if cv2.getWindowProperty('UC480',cv2.WND_PROP_VISIBLE) < 1:   
        break

uc480.end_video()
