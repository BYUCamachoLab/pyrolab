import time

from pyrolab.drivers.cameras.thorcam import ThorCamClient

from pyrolab.api import NameServerConfiguration
import numpy as np
import cv2

nscfg = NameServerConfiguration(host="camacholab.ee.byu.edu")
nscfg.update_pyro_config()

cam1 = ThorCamClient()
cam2 = ThorCamClient()
cam1.connect("pymtech.fury")
cam2.connect("asgard.rocket")
cam1.color = False
cam2.color = False
cam1.roi_shape = [500,500]
cam2.roi_shape = [500,500]
# cam.roi_pos = [150,150]
cam1.exposure = 90
cam2.exposure = 90
cam1.brightness = 10
cam2.brightness = 20
cam1.start_stream()
cam2.start_stream()
cam1.await_stream()
cam2.await_stream()

while(True):
    frame1 = cam1.get_frame()
    frame2 = cam2.get_frame()
    cv2.imshow('ThorCam',np.concatenate((frame1,frame2),axis=1))  #paint the image to the cv2 window
    # cv2.imshow('ThorCam',frame2)  #paint the image to the cv2 window
    keyCode = cv2.waitKey(30)

    if cv2.getWindowProperty('ThorCam',cv2.WND_PROP_VISIBLE) < 1:   
        break
        

cam1.end_stream()
cam2.end_stream()
time.sleep(1)
cam1.close()
cam2.close()
