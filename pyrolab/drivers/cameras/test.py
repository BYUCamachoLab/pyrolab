from pyrolab.drivers.cameras.amcam import DM756_U830, DM756_U830Client

import cv2
import numpy as np

cam = DM756_U830()
cam.connect()

while cam.cam_connected:
    data = cam.pop_data()
    print(type(data))
    if data is not None:
        img = np.frombuffer(data, np.uint8)
        # print(img.shape)
        img = img.reshape(3, 3840, 2160, order='C')
        img.shape = (2160, 3840, 3)
        img = np.flip(img, [0,2])
        cv2.namedWindow('frame', cv2.WINDOW_NORMAL)
        cv2.imshow('frame', img)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
        
cam.close()