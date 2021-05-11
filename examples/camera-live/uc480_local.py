# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
-------------------------------------------------------------------------------
Example to connect to and stream a live video from a Thorlabs UC480 microscope
locally.
Author: David Hill (https://github.com/hillda3141)
Modified: 5/4/2021
Repo: https://github.com/BYUCamachoLab/pyrolab/examples/camera-live
"""

from pyrolab.drivers.cameras.uc480 import UC480
import numpy as np
import cv2
import time
import pickle

BRIGHTNESS = 5  #be able to make the recieved video brighter or darker, this
                #does nothing to the raw data, it is post-processing,
                #range: 0-10, 5 is no change
PIXEL_MAX = 255 #the maximum number that a pixel can hold (255 at bit depth 8)
EXPOSURE = 65   #the exposure that the camera uses, this actually changes the
                #raw camera data by changing the exposure time of the sensor
SER_NUMBER = 4103247225 #serial number of the Thorlabs camera
COLOR = True   #should the camera transmit colored data or grayscale?

def bayer_convert(bayer):
    """
    Coverts the raw data to something that can be displayed on-screen.

    Parameters
    ----------
    bayer : numpy array
        this is the raw data that is recieved from the camera    
    """
    if(COLOR):  #if the data is in color, put the numpy array into BGR form
        frame_height = bayer.shape[0]//2
        frame_width = bayer.shape[1]//2

        ow = (bayer.shape[0]//4) * 4
        oh = (bayer.shape[1]//4) * 4

        R  = bayer[0::2, 0::2]
        B  = bayer[1::2, 1::2]
        G0 = bayer[0::2, 1::2]
        G1 = bayer[1::2, 0::2]
        G = G0[:oh,:ow]//2 + G1[:oh,:ow]//2

        bayer_R = np.array(R, dtype=np.uint8).reshape(frame_height, frame_width)
        bayer_G = np.array(G, dtype=np.uint8).reshape(frame_height, frame_width)
        bayer_B = np.array(B, dtype=np.uint8).reshape(frame_height, frame_width)

        dStack = np.clip(np.dstack((bayer_B*(BRIGHTNESS/5),bayer_G*(BRIGHTNESS/5),
                         bayer_R*(BRIGHTNESS/5))),0,PIXEL_MAX).astype('uint8')
    else:   #if the data is grayscale, put it into BGR form
        frame_height = bayer.shape[0]
        frame_width = bayer.shape[1]
        bayer_T = np.array(bayer, dtype=np.uint8).reshape(frame_height,
                           frame_width)
        dStack = np.clip((np.dstack(((bayer_T)*(BRIGHTNESS/5),
                         (bayer_T)*(BRIGHTNESS/5),(bayer_T)*(BRIGHTNESS/5)))),0,
                         PIXEL_MAX).astype('uint8')
    return dStack

    
cam = UC480(ser_no=SER_NUMBER,exposure=EXPOSURE)    #start a UC480 object with
                                                    #the correct serial number
                                                    #and exposure time

cam.start_capture(COLOR,True)   #start pulling frames from the camera
time.sleep(0.5) #wait for the camera to start the capture

while(True):    #loop to get frames
    t_init = time.time()
    dStack = bayer_convert(cam.get_frame()) #get most recent frame
    cv2.imshow('UC480_1',dStack)  #paint it to the cv2 window
    keyCode = cv2.waitKey(1)
    
    #if window is exited, break from the loop
    if cv2.getWindowProperty('UC480_1',cv2.WND_PROP_VISIBLE) < 1:
        break
    # time.sleep(0.5)
    pfs = 1.0/(time.time()-t_init)
    print("pfs: " + str(pfs))

cam.close() #close the camera connection
