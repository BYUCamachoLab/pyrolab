from pyrolab.api import locate_ns, Proxy
import numpy as np
import cv2
import sys
import socket
import pickle
import time

HEADERSIZE = 10
BRIGHTNESS = 5

def bayer_convert(bayer):
    dStack = np.clip((np.dstack(((0.469 + bayer*0.75 - (bayer^2)*0.003)*(BRIGHTNESS/5),(bayer*0.95)*(BRIGHTNESS/5),(0.389 + bayer*1.34 - (bayer^2)*0.004)*(BRIGHTNESS/5)))),0,255).astype('uint8')
    return dStack

ns = locate_ns(host="camacholab.ee.byu.edu")
cam = Proxy(ns.lookup("UC480"))

cam.start()
cam.start_capture()
clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
clientsocket.connect(('10.32.112.191', 2222))

while(True):
    msg = b''
    new_msg = True
    msg_len = None
    imList = None
    while True:
        if new_msg:
            sub_msg = clientsocket.recv(HEADERSIZE)
            msg_len = int((sub_msg[:HEADERSIZE]))
            new_msg = False
        else:
            sub_msg = clientsocket.recv(32800)
            msg += sub_msg
            if len(msg) == msg_len:
                imList = pickle.loads(msg)
                break
                
    bayer = np.array(imList, dtype=np.uint8).reshape(512, 640)
    dStack = bayer_convert(bayer)

    cv2.imshow('scope',dStack)
    keyCode = cv2.waitKey(1)
    
    if cv2.getWindowProperty('scope',cv2.WND_PROP_VISIBLE) < 1:
        clientsocket.send(b'b')     
        break
    clientsocket.send(b'g')

cam.close()