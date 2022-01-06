import time

from pyrolab.drivers.cameras.thorcam import ThorCamClient

from pyrolab.api import NameServerConfiguration
import numpy as np
import cv2

nscfg = NameServerConfiguration(host="camacholab.ee.byu.edu")
nscfg.update_pyro_config()

uc480 = ThorCamClient()
uc480.connect("asgard.rocket")
uc480.color = False
print(uc480.color)
print(uc480.exposure)
print(uc480.brightness)

uc480.start_stream()
time.sleep(1)
count = 0
while(True):
    cv2.imshow('ThorCam',uc480.get_frame())  #paint the image to the cv2 window
    keyCode = cv2.waitKey(30)

    if cv2.getWindowProperty('ThorCam',cv2.WND_PROP_VISIBLE) < 1:   
        break
    
    count = count + 1
    if count == 100:
        uc480.exposure = 20

uc480.end_stream()
