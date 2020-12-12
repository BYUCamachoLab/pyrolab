from win32event import CreateMutex
from win32api import GetLastError
from winerror import ERROR_ALREADY_EXISTS
from sys import exit

handle = CreateMutex(None, 1, 'Camera Service')

if GetLastError() == ERROR_ALREADY_EXISTS:
    # Take appropriate action, as this is the second instance of this script.
    print('An instance of this application is already running.')
    exit(1)

from Pyro5.api import expose, locate_ns, Daemon, config, behavior

def get_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

import os
os.environ['PATH'] = "C:\\Program Files\\ThorLabs\\Scientific Imaging\\ThorCam" + ";" + os.environ['PATH']  #this path must be change to the location of the .dll files from Thorlabs

import time
from thorlabs_kinesis import thor_camera as tc

import numpy as np

from ctypes import *

c_word = c_ushort
c_dword = c_ulong

import pyrolab.api

@expose
class UC480:
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

    def get_image(self):
        im = np.frombuffer(self.meminfo[0], c_ubyte).reshape(self.roi_shape[1], self.roi_shape[0])
        return im

    def set_pixel_clock(self, clockspeed):
        pixelclock = c_uint(clockspeed)
        i = tc.PixelClock(self.handle, 6, byref(pixelclock), sizeof(pixelclock))
        print("Pixel:")
        print(i)

    def start_capture(self, waitMode):
        tc.StartCapture(self.handle, waitMode)

    def stop_capture(self, waitMode):
        tc.FreeMemory(self.handle, self.meminfo[0], self.meminfo[1])
        #self.epix.pxd_goUnLive(0x1)
        tc.StopCapture(self.handle, waitMode)
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

if __name__ == "__main__":
    config.HOST = get_ip()
    config.SERVERTYPE = "multiplex"
    daemon = Daemon()
    ns = locate_ns(host="camacholab.ee.byu.edu")

    uri = daemon.register(UC480)
    ns.register("UC480", uri)
    try:
        daemon.requestLoop()
    finally:
        ns.remove("UC480")