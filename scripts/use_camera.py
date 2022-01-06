import time

from pyrolab.drivers.cameras.thorcam import ThorCamClient

from pyrolab.api import NameServerConfiguration
import numpy as np
import cv2

nscfg = NameServerConfiguration(host="camacholab.ee.byu.edu")
nscfg.update_pyro_config()

cam = ThorCamClient()
cam.connect("pymtech.fury")

cam.start_stream()
cam.await_stream()

while(True):
    frame = cam.get_frame()
    print(frame.shape)
    cv2.imshow('ThorCam',frame)  #paint the image to the cv2 window
    keyCode = cv2.waitKey(30)

    if cv2.getWindowProperty('ThorCam',cv2.WND_PROP_VISIBLE) < 1:   
        break
        

cam.end_stream()
