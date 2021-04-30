from pyrolab.api import locate_ns, Proxy
from pyrolab.drivers.cameras.uc480 import UC480
from thorlabs_kinesis import thor_camera as tc
import numpy as np
import cv2
import socket
import pickle
import time
from ctypes import *
from PIL import Image
from datetime import datetime

HEADERSIZE = 10
BRIGHTNESS = 5
PORT = 2222
SER_NUMBER = 4103247225
COLOR = True

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


cam = UC480(ser_no=SER_NUMBER,exposure=65)

ip_address = cam.start_capture(COLOR)
print(ip_address)
clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
clientsocket.connect((str(ip_address), PORT))

now = datetime.now()
dt_string = now.strftime("rec_"+str(SER_NUMBER)+"/%Y-%m-%d_%H-%M-%S.avi")
fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter(dt_string,fourcc, 4.0, (640,512))

time_s = 0
frame_rate = 0
count = -1
while(True):
    if(count >= 0):
        t = time.time() - time_s
        frame_rate = (frame_rate*count + 1/t)/(count + 1)   
        print(frame_rate)

    time_s = time.time()
    count = count + 1

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

    #frame = Image.fromarray(dStack)
    out.write(dStack)

    cv2.imshow('scope',dStack)
    keyCode = cv2.waitKey(1)
    
    if cv2.getWindowProperty('scope',cv2.WND_PROP_VISIBLE) < 1:
        clientsocket.send(b'b')     
        break
    clientsocket.send(b'g')

out.release()
cam.close()