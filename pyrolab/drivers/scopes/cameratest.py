import uc480 as cam
import numpy as np
import cv2
import sys

cam = cam.UC480()
cam.open()
cam.set_pixel_clock(24)
cam.set_color_mode(mode=11)
cam.set_framerate(10)
cam.set_exposure(400)

cam.initialize_memory(pixelbytes=8)
cam.start_capture()

while(True):
    bayer = cam.get_image()
    dStack = bayer_convert(bayer)
    img = increase_brightness(dStack, 40)

    cv2.imshow('scope',dStack)
    keyCode = cv2.waitKey(10)
    if cv2.getWindowProperty('scope',cv2.WND_PROP_VISIBLE) < 1:        
        break

cam.stop_live_capture()
cam.close()


def bayer_convert(bayer):
    w = bayer.shape[0]
    h = bayer.shape[1]

    ow = (w//4) * 4
    oh = (h//4) * 4

    R  = bayer[0::2, 0::2]     # rows 0,2,4,6 columns 0,2,4,6
    B  = bayer[1::2, 1::2]     # rows 1,3,5,7 columns 1,3,5,7
    G0 = bayer[0::2, 1::2]     # rows 0,2,4,6 columns 1,3,5,7
    G1 = bayer[1::2, 0::2]     # rows 1,3,5,7 columns 0,2,4,6

    # Chop any left-over edges and average the 2 Green values
    R = R[:oh,:ow]
    B = B[:oh,:ow]
    G = G0[:oh,:ow]//2 + G1[:oh,:ow]//2

    dStack = np.dstack((B,G,R))
    return dStack

def increase_brightness(img, value):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    lim = 255 - value
    v[v > lim] = 255
    v[v <= lim] += value

    final_hsv = cv2.merge((h, s, v))
    img = cv2.cvtColor(final_hsv, cv2.COLOR_HSV2BGR)
    return img