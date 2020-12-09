import os
os.environ['PATH'] = "C:\\Program Files\\ThorLabs\\Scientific Imaging\\ThorCam" + ";" + os.environ['PATH']  #this path must be change to the location of the .dll files from Thorlabs

import time
from thorlabs_kinesis import thor_camera as tc

import numpy as np

from ctypes import *

c_word = c_ushort
c_dword = c_ulong

class UC480(object):
    def __init__(self):      
        self.bit_depth = None
        self.camera = None
        self.handle = None
        self.meminfo = None
        self.exposure = None
        self.framerate = None
        self.img_size = None

    def open(self, bit_depth=8, img_size=(1023, 1278), camera="ThorCam FS"):
        print(tc.GetCameraList)
        num = c_int(0)
        tc.GetNumberOfCameras(byref(num))
        print(num.value)
        self.bit_depth = bit_depth
        self.camera = camera
        self.img_size = img_size
        
        self.handle = c_int(0)
        i = tc.InitCamera(byref(self.handle))     
        #print("Display Mode:")
        tc.SetDisplayMode(self.handle, c_int(32768)) 
        #print(i)
        if i == 0:
            print("ThorCam opened successfully.")
        else:
            print("Opening the ThorCam failed with error code "+str(i))

    def close(self):
        if self.handle != None:
            self.stop_live_capture()
            i = tc.ExitCamera(self.handle) 
            if i == 0:
                print("ThorCam closed successfully.")
            else:
                print("Closing ThorCam failed with error code "+str(i))
        else:
            return

    def get_image(self):
        im = np.frombuffer(self.meminfo[0], c_ubyte).reshape(self.img_size[1], self.img_size[0])
        return im

    def set_pixel_clock(self, clockspeed):
        pixelclock = c_uint(clockspeed)
        tc.PixelClock(self.handle, 6, byref(pixelclock), sizeof(pixelclock))

    def start_capture(self, waitMode):
        tc.StartCapture(self.handle, waitMode)

    def stop_capture(self, waitMode):
        self.uc480.is_FreeImageMem(self.handle, self.meminfo[0], self.meminfo[1])
        #self.epix.pxd_goUnLive(0x1)
        self.uc480.is_StopLiveVideo(self.handle, waitMode)
        print("unlive now")
        
    def initialize_memory(self, pixelbytes=8):
        if self.meminfo != None:
            self.uc480.is_FreeImageMem(self.handle, self.meminfo[0], self.meminfo[1])
        
        xdim = self.img_size[0]
        ydim = self.img_size[1]
        #print(xdim)
        #print(ydim)
        imagesize = xdim*ydim
        #print(imagesize)
            
        memid = c_int(0)
        c_buf = (c_ubyte * imagesize)(0)
        #print(c_buf)

        tc.AllocateMemory(self.handle, xdim, ydim, pixelbytes, c_buf, byref(memid))
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
        tc.SetColorMode(self.handle, mode) #11 means raw 8-bit, 6 means gray 8-bit