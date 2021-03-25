from pyrolab.api import locate_ns, Proxy
import numpy as np
import cv2
import sys
import socket
import pickle
import time

HEADERSIZE = 10
BRIGHTNESS = 5
PORT = 2222
SER_NUMBER = 4103238947
COLOR = False

def bayer_convert(bayer):
    if(COLOR):
        ow = (bayer.shape[0]//4) * 4
        oh = (bayer.shape[1]//4) * 4

        R  = bayer[0::2, 0::2]
        B  = bayer[1::2, 1::2]
        G0 = bayer[0::2, 1::2]
        G1 = bayer[1::2, 0::2]
        G = G0[:oh,:ow]//2 + G1[:oh,:ow]//2
        bayer_R = np.array(R, dtype=np.uint8).reshape(512, 640)
        bayer_G = np.array(G, dtype=np.uint8).reshape(512, 640)
        bayer_B = np.array(B, dtype=np.uint8).reshape(512, 640)

        dStack = np.clip(np.dstack((bayer_B*(BRIGHTNESS/5),bayer_G*(BRIGHTNESS/5),bayer_R*(BRIGHTNESS/5))),0,255).astype('uint8')
    else:
        bayer_T = np.array(bayer, dtype=np.uint8).reshape(512, 640)
        dStack = np.clip((np.dstack(((0.469 + bayer_T*0.75 - (bayer_T^2)*0.003)*(BRIGHTNESS/5),(bayer_T*0.95)*(BRIGHTNESS/5),(0.389 + bayer_T*1.34 - (bayer_T^2)*0.004)*(BRIGHTNESS/5)))),0,255).astype('uint8')
    #dStack = np.clip(np.dstack((bayer,bayer,bayer)),0,255).astype('uint8')
    return dStack

ns = locate_ns(host="camacholab.ee.byu.edu")
cam = Proxy(ns.lookup("UC480"))

cam.start(ser_no = SER_NUMBER, port = PORT)
ip_address = cam.start_capture(COLOR)
print(ip_address)
clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
clientsocket.connect((str(ip_address), PORT))

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
                
    dStack = bayer_convert(imList)

    cv2.imshow('scope',dStack)
    keyCode = cv2.waitKey(1)
    
    if cv2.getWindowProperty('scope',cv2.WND_PROP_VISIBLE) < 1:
        clientsocket.send(b'b')     
        break
    clientsocket.send(b'g')

cam.close()