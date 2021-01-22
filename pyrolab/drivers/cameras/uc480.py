import socket
import pickle
import time
import threading

from Pyro5.api import expose

import os
os.environ['PATH'] = "C:\\Program Files\\ThorLabs\\Scientific Imaging\\ThorCam" + ";" + os.environ['PATH']  #this path must be change to the location of the .dll files from Thorlabs

from thorlabs_kinesis import thor_camera as tc

import numpy as np

#np.set_printoptions(threshold=sys.maxsize)

from ctypes import *

c_word = c_ushort
c_dword = c_ulong

HEADERSIZE = 10

import pyrolab.api

@expose
class UC480:

    handle = None
    camera = None
    bit_depth = None
    meminfo = None
    roi_shape = None
    roi_pos = None
    framerate = None
    video_thread = None
    stop_video = None
    serversocket = None
    clientsocket = None
    start_socket = None

    def __init__(self):
        pass

    def open(self, bit_depth=8, camera="ThorCam FS"):
        print(tc.GetCameraList)
        num = c_int(0)
        tc.GetNumberOfCameras(byref(num))
        print(num.value)
        self.bit_depth = bit_depth
        self.camera = camera
        
        self.handle = c_int(0)
        i = tc.InitCamera(byref(self.handle))     
        #print("Display Mode:")
        tc.SetDisplayMode(self.handle, c_int(32768)) 
        #print(i)
        if i == 0:
            print("ThorCam opened successfully.")
        else:
            print("Opening the ThorCam failed with error code "+str(i))

    def close(self, waitMode):
        if self.handle != None:
            self.stop_capture(waitMode)
            i = tc.ExitCamera(self.handle) 
            if i == 0:
                print("ThorCam closed successfully.")
            else:
                print("Closing ThorCam failed with error code "+str(i))
        else:
            return

    def _get_image(self):
        bayer = np.frombuffer(self.meminfo[0], c_ubyte).reshape(self.roi_shape[1], self.roi_shape[0])

        ow = (bayer.shape[0]//4) * 4
        oh = (bayer.shape[1]//4) * 4

        R  = bayer[0::2, 0::2]
        B  = bayer[1::2, 1::2]
        G0 = bayer[0::2, 1::2]
        G1 = bayer[1::2, 0::2]

        GRAY = R[:oh,:ow]//3 + B[:oh,:ow]//3 + (G0[:oh,:ow]//2 + G1[:oh,:ow]//2)//3

        #print(np.dstack((B,G,R)))

        #print(im)
        #image = GRAY.tolist()
        msg = pickle.dumps(GRAY)
        #print(len(msg))
        msg = bytes(f'{len(msg):<{HEADERSIZE}}', "utf-8") + msg
        return msg

    def _video_loop(self):
        while not self.stop_video.is_set():
            if self.start_socket==True:
                while True:
                    print("setting up server...")
                    self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.serversocket.bind((socket.gethostname(), 2222))
                    self.serversocket.listen(5)
                    self.clientsocket, address = self.serversocket.accept()
                    print("server set up")
                    self.start_socket = False
                    break
            msg = self._get_image()
            #print("image grabbed")
            self.clientsocket.send(msg)
            #print("message sent")
            while True:
                check_msg = self.clientsocket.recv(2)
                break
        
    def set_pixel_clock(self, clockspeed):
        pixelclock = c_uint(clockspeed)
        i = tc.PixelClock(self.handle, 6, byref(pixelclock), sizeof(pixelclock))
        print("Pixel:")
        print(i)

    def start_capture(self, waitMode):
        tc.StartCapture(self.handle, waitMode)
        self.start_socket = True
        self.stop_video = threading.Event()
        self.video_thread = threading.Thread(target=self._video_loop, args=())
        self.video_thread.start()

    def stop_capture(self, waitMode):
        tc.FreeMemory(self.handle, self.meminfo[0], self.meminfo[1])
        #self.epix.pxd_goUnLive(0x1)
        tc.StopCapture(self.handle, waitMode)
        self.clientsocket.close()
        self.stop_video.set()
        print("unlive now")
        
    def initialize_memory(self, pixelbytes=8):
        if self.meminfo != None:
            tc.FreeMemory(self.handle, self.meminfo[0], self.meminfo[1])
        
        xdim = self.roi_shape[0]
        ydim = self.roi_shape[1]
        #print(xdim)
        #print(ydim)
        imagesize = xdim*ydim
        #print(imagesize)
            
        memid = c_int(0)
        c_buf = (c_ubyte * imagesize)(0)
        #print(c_buf)

        tc.AllocateMemory(self.handle, xdim, ydim, c_int(pixelbytes), c_buf, byref(memid))
        #print(c_buf)
        #print(memid)
        tc.SetImageMemory(self.handle, c_buf, memid)
        self.meminfo = [c_buf, memid]
    
    def set_exposure(self, exposure):
        #exposure should be given in ms
        exposure_c = c_double(exposure)
        tc.SetExposure(self.handle, 12 , exposure_c, sizeof(exposure_c))
        self.exposure = exposure_c.value
    
    def set_framerate(self, fps):
        #must reset exposure after setting framerate
        #frametime should be givin in ms.        
        set_framerate = c_double(0)
        tc.SetFrameRate(self.handle, c_double(fps), byref(set_framerate))
        self.framerate = set_framerate.value

    def set_color_mode(self, mode=11):
        i = tc.SetColorMode(self.handle, mode) #11 means raw 8-bit, 6 means gray 8-bit
        print("Color Mode:")
        print(i)

    def set_roi_shape(self, roi_shape):
        AOI_size = tc.IS_2D(roi_shape[0], roi_shape[1]) #Width and Height
            
        i = tc.AOI(self.handle, 5, byref(AOI_size), 8)#5 for setting size, 3 for setting position
        tc.AOI(self.handle, 6, byref(AOI_size), 8)#6 for getting size, 4 for getting position
        self.roi_shape = [AOI_size.s32X, AOI_size.s32Y]
        print(self.roi_shape)
        if i == 0:
            print("ThorCam ROI size set successfully.")
        else:
            print("Set ThorCam ROI size failed with error code "+str(i))

    def set_roi_pos(self, roi_pos):
        AOI_pos = tc.IS_2D(roi_pos[0], roi_pos[1]) #Width and Height
            
        i = tc.AOI(self.handle, 3, byref(AOI_pos), 8 )#5 for setting size, 3 for setting position
        tc.AOI(self.handle, 4, byref(AOI_pos), 8 )#6 for getting size, 4 for getting position
        self.roi_pos = [AOI_pos.s32X, AOI_pos.s32Y]
        print(self.roi_pos)
        
        if i == 0:
            print("ThorCam ROI position set successfully.")
        else:
            print("Set ThorCam ROI pos failed with error code "+str(i))