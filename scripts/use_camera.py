import time

from pyrolab.drivers.cameras.thorcam import ThorCamClient

from pyrolab.api import NameServerConfiguration
import numpy as np
import cv2

nscfg = NameServerConfiguration(host="camacholab.ee.byu.edu")
nscfg.update_pyro_config()

cam = ThorCamClient()
cam.connect("pymtech.fury")
cam.color = True
# cam.roi_shape = [400,300]
# cam.roi_pos = [0,0]
# cam.exposure = 30
# cam.brightness = 10
cam.start_stream()
cam.await_stream()

# time.sleep(3)

while(True):
    cv2.imshow('ThorCam',cam.get_frame())  #paint the image to the cv2 window
    keyCode = cv2.waitKey(30)

    if cv2.getWindowProperty('ThorCam',cv2.WND_PROP_VISIBLE) < 1:   
        break
        

cam.end_stream()
time.sleep(1)
cam.close()
