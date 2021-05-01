from Pyro5.api import locate_ns, Proxy
import numpy as np
import cv2
import socket
import pickle
import time
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
        dStack = dStack = np.clip((np.dstack(((bayer_T)*(BRIGHTNESS/5),(bayer_T)*(BRIGHTNESS/5),(bayer_T)*(BRIGHTNESS/5)))),0,255).astype('uint8')
    #dStack = np.clip(np.dstack((bayer,bayer,bayer)),0,255).astype('uint8')
    return dStack

ns = locate_ns(host="camacholab.ee.byu.edu")
objs = str(ns.list())
while(True):
    temp_str = objs[objs.find('\'')+1:-1]
    temp_obj = temp_str[0:temp_str.find('\'')]
    if(temp_obj[0:6] ==  "UC480_"):
        temp_ser_no = int(temp_obj[6:len(temp_obj)])
        print(temp_ser_no)
        if(temp_ser_no == SER_NUMBER):
            cam_str = temp_obj 
    if(objs.find(',') == -1):
        break
    objs = objs[objs.find(',')+1:-1]
try:
    cam_str
    print(cam_str)
except NameError:
    raise Exception("Camera with serial number " + str(SER_NUMBER) + " could not be found")

cam = Proxy(ns.lookup(cam_str))

cam.start(exposure=65)
ip_address = cam.start_capture(COLOR,False)
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