# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Santec Tunable Semiconductor Laser 550 (TSL550)
-----------------------------------------------
Driver for the Santec TSL-550 Tunable Laser.
Contributors
 * David Hill (https://github.com/hillda3141)
 * Sequoia Ploeg (https://github.com/sequoiap)
Repo: https://github.com/BYUCamachoLab/pyrolab
"""

import socket
import pickle
import time
import threading

from Pyro5.api import expose
from thorlabs_kinesis import thor_camera as tc

import numpy as np

from ctypes import *

c_word = c_ushort
c_dword = c_ulong

HEADERSIZE = 10

import pyrolab.api

@expose
class UC480:

    """ A Thorlabs UC480 Camera.
    This assumes there is only one camera connected to the computer.
    ----------
    handle : handle
        c-type handle to reference camera (serial port, etc)
    camera: str
        camera name
    bit_depth : int
        the number of bits used for each pixel (usually is 8)
    meminfo : array(int)
        points to the memory location where captured frames are stored
    roi_shape : array(int)
        dimentions of the image that is taken by the camera (usually 1024 x 1280)
    roi_pos : array(int)
        position of the top left corner of the roi (region of interest) in relation to the sensor array (usaually 0,0)
    framerate : int
        the framerate of the camera in frames per second
    video_thread : thread
        seperate thread used to run parrell to the main loop that streams the video fromt he camera
    stop_video : threading.Event (similar to boolean)
        this is used to end the video streaming by ending the parrellel "video_thread"
    serversocket : socket
        socket that represents the server computer (running on port 2222)
    clientsocket : socket
        socket that represents the client computer
    start_socket : boolean
        if true, initiates the socket server connection
    Attributes
    ----------
    HEADERSIZE : int
        the size of the header file used to communicate the size of the message (10 bytes is a safe size)
    """

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
    enabled = False

    def __init__(self):
        self.enabled = True
        pass

    def open(self, bit_depth=8, camera="ThorCam FS"):
        """
        Opens the serial communication with the Thorlabs camera and sets
        some low-level values, including the bit depth and camera name.
        """
        if self.enabled == False:
            raise Exception("Device is locked")

        num = c_int(0)
        tc.GetNumberOfCameras(byref(num))
        self.bit_depth = bit_depth
        self.camera = camera
        
        self.handle = c_int(0)
        i = tc.InitCamera(byref(self.handle))     
        tc.SetDisplayMode(self.handle, c_int(32768)) 
        if i != 0:
            raise Exception("Opening the ThorCam failed with error code "+str(i))

    def close(self, waitMode):
        """
        Calls self.stop_capture to free memory and end the socket server
        and then closes serial communication with the camera.
        """
        if self.enabled == False:
            raise Exception("Device is locked")
        
        if self.handle != None:
            self.stop_capture(waitMode)
            i = tc.ExitCamera(self.handle) 
            if i != 0:
                raise Exception("Closing ThorCam failed with error code "+str(i))
        else:
            return

    def _get_image(self):
        """
        Retrieves the last frame from the memory buffer, processes
        it into a gray-scale image, and serializes it using the pickle
        library. The header is then added to inform the client how long
        the message is. This should not be called from the client. It
        will be called from the function _video_loop() which is on a
        parrallel thread with Pyro5.
        """
        if self.enabled == False:
            raise Exception("Device is locked")
        
        bayer = np.frombuffer(self.meminfo[0], c_ubyte).reshape(self.roi_shape[1], self.roi_shape[0])

        ow = (bayer.shape[0]//4) * 4
        oh = (bayer.shape[1]//4) * 4

        R  = bayer[0::2, 0::2]
        B  = bayer[1::2, 1::2]
        G0 = bayer[0::2, 1::2]
        G1 = bayer[1::2, 0::2]

        GRAY = R[:oh,:ow]//3 + B[:oh,:ow]//3 + (G0[:oh,:ow]//2 + G1[:oh,:ow]//2)//3

        msg = pickle.dumps(GRAY)
        msg = bytes(f'{len(msg):<{HEADERSIZE}}', "utf-8") + msg
        return msg

    def _video_loop(self):
        """
        This function is called as a seperate thread when streaming is initiated.
        It will loop, sending frame by frame accross the socket connection,
        until the threading.Event() stop_video is triggered.
        """
        if self.enabled == False:
            raise Exception("Device is locked")
        
        bad = False
        while not self.stop_video.is_set():
            if bad == False:
                if self.start_socket==True:
                    while True:
                        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.serversocket.bind((socket.gethostname(), 2222))
                        self.serversocket.listen(5)
                        self.clientsocket, address = self.serversocket.accept()
                        self.start_socket = False
                        break
                msg = self._get_image()
                self.clientsocket.send(msg)
                while True:
                    check_msg = self.clientsocket.recv(2)
                    if(check_msg == b'b'):
                        bad = True
                    break
        
    def set_pixel_clock(self, clockspeed):
        """
        Sets the clockspeed of the camera, usually in the range of 24.
        """
        if self.enabled == False:
            raise Exception("Device is locked")
        
        pixelclock = c_uint(clockspeed)
        i = tc.PixelClock(self.handle, 6, byref(pixelclock), sizeof(pixelclock))

    def start_capture(self, waitMode):
        """
        This starts the capture from the camera to the allocated
        memory location as well as starts a new parallel thread
        for the socket server to stream from memory to the client.
        """
        if self.enabled == False:
            raise Exception("Device is locked")
        
        tc.StartCapture(self.handle, waitMode)
        self.start_socket = True
        self.stop_video = threading.Event()
        self.video_thread = threading.Thread(target=self._video_loop, args=())
        self.video_thread.start()

    def stop_capture(self, waitMode):
        """
        This frees the memory used for storing the frames then triggers
        the stop_video event which will end the parrallel socket thread.
        """
        if self.enabled == False:
            raise Exception("Device is locked")
        
        tc.FreeMemory(self.handle, self.meminfo[0], self.meminfo[1])
        tc.StopCapture(self.handle, waitMode)
        self.clientsocket.close()
        self.stop_video.set()
        
    def initialize_memory(self, pixelbytes=8):
        """
        Initializes the memory for holding the most recent frame from the camera.
        """
        if self.enabled == False:
            raise Exception("Device is locked")
        
        if self.meminfo != None:
            tc.FreeMemory(self.handle, self.meminfo[0], self.meminfo[1])
        
        xdim = self.roi_shape[0]
        ydim = self.roi_shape[1]
        imagesize = xdim*ydim
            
        memid = c_int(0)
        c_buf = (c_ubyte * imagesize)(0)

        tc.AllocateMemory(self.handle, xdim, ydim, c_int(pixelbytes), c_buf, byref(memid))
        tc.SetImageMemory(self.handle, c_buf, memid)
        self.meminfo = [c_buf, memid]
    
    def set_exposure(self, exposure):
        """
        This sets the exposure of the camera in milliseconds (90 is a good exposure value).
        """
        if self.enabled == False:
            raise Exception("Device is locked")
        
        exposure_c = c_double(exposure)
        tc.SetExposure(self.handle, 12 , exposure_c, sizeof(exposure_c))
        self.exposure = exposure_c.value
    
    def set_framerate(self, fps):
        """
        Sets the framerate of the camera (fps). After calling
        this function you must reset the exposure.
        """  
        if self.enabled == False:
            raise Exception("Device is locked")
            
        s_framerate = c_double(0)
        tc.SetFrameRate(self.handle, c_double(fps), byref(s_framerate))
        self.framerate = s_framerate.value

    def set_color_mode(self, mode=11):
        """
        This sets the mode of image that is taken, almost always
        use 11 which will give you the raw photosensor data in the format:
            | R  G0 |...
            | G1  B |...
              .   .
              .   .
              .   .
        This data is interpreted in the _get_image() function.
        """
        if self.enabled == False:
            raise Exception("Device is locked")
        
        i = tc.SetColorMode(self.handle, mode) #11 means raw 8-bit, 6 means gray 8-bit

    def set_roi_shape(self, roi_shape):
        """
        Sets the dimmenstions of the region of interest (roi)
        """
        if self.enabled == False:
            raise Exception("Device is locked")
        
        AOI_size = tc.IS_2D(roi_shape[0], roi_shape[1]) #Width and Height
            
        i = tc.AOI(self.handle, 5, byref(AOI_size), 8)#5 for setting size, 3 for setting position
        tc.AOI(self.handle, 6, byref(AOI_size), 8)#6 for getting size, 4 for getting position
        self.roi_shape = [AOI_size.s32X, AOI_size.s32Y]

    def set_roi_pos(self, roi_pos):
        """
        Sets the origin position of the region of interest (usually (0,0))
        """
        if self.enabled == False:
            raise Exception("Device is locked")
        
        AOI_pos = tc.IS_2D(roi_pos[0], roi_pos[1]) #Width and Height
            
        i = tc.AOI(self.handle, 3, byref(AOI_pos), 8 )#5 for setting size, 3 for setting position
        tc.AOI(self.handle, 4, byref(AOI_pos), 8 )#6 for getting size, 4 for getting position
        self.roi_pos = [AOI_pos.s32X, AOI_pos.s32Y]