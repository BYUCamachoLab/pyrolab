# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
-----------------------------------------------
Driver for a Thorlabs Microscope.
Author: David Hill (https://github.com/hillda3141)
Repo: https://github.com/BYUCamachoLab/pyrolab/pyrolab/drivers/cameras

import socket
import pickle
import threading
import numpy as np
from ctypes import *
from Pyro5.errors import PyroError
from Pyro5.api import expose
from thorlabs_kinesis import thor_camera as tc
import pyrolab.api

@expose
class UC480:

    """
    Attributes
    ----------
    HEADERSIZE : int
        the size of the header file used to communicate the size of the message (10 bytes is a safe size)
    """
    HEADERSIZE = 10

    def __init__(self):
        self._activated = True
        pass

    def start(self, bit_depth=8, camera="ThorCam FS", pixel_clock=24, color_mode=11, roi_shape=(1024, 1280), roi_pos=(0,0), framerate=10, exposure=90, pixelbytes=8):
        """
        Opens the serial communication with the Thorlabs camera and sets
        some low-level values, including the bit depth and camera name.

        Parameters
        ----------
        bit_depth : int
            the number of bits used for each pixel (usually is 8)
        camera: string
            camera name
        pixel_clock: int
            clock speed of the camera
        color_mode: int
            mode of color that the camera returns data in. 11 returns raw format:
            | R  G0 |...
            | G1  B |...
              .   .
              .   .
              .   .
        roi_shape : array(int)
            dimentions of the image that is taken by the camera (usually 1024 x 1280)
        roi_pos : array(int)
            position of the top left corner of the roi (region of interest) in relation to the sensor array (usaually 0,0)
        framerate : int
            the framerate of the camera in frames per second
        exposure: int
            in milliseconds, the time the shutter is open on the camera (90 default)
        pixelbytes: int
            the amount of memory space allocated per pixel in bytes
        
        Raises
        ------
        PyroError("Opening the ThorCam failed with error code "+str(i))
            Error to signal that the connection with the camera could not be established. Usually means that the last person using
            it did not close out of it correctly or is still accessing it.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")

        num = c_int(0)
        tc.GetNumberOfCameras(byref(num))
        self.bit_depth = bit_depth
        self.camera = camera
        
        self.handle = c_int(0)
        i = tc.InitCamera(byref(self.handle))     
        tc.SetDisplayMode(self.handle, c_int(32768)) 

        if i != 0:
            raise PyroError("Opening the ThorCam failed with error code "+str(i))

        self.meminfo = None

        self.set_pixel_clock(pixel_clock)
        self.set_color_mode(color_mode)
        self.set_roi_shape(roi_shape)
        self.set_roi_pos(roi_pos)
        self.set_framerate(framerate)
        self.set_exposure(exposure)
        self.initialize_memory(pixelbytes)

    def _get_image(self):
        """
        Retrieves the last frame from the memory buffer, processes
        it into a gray-scale image, and serializes it using the pickle
        library. The header is then added to inform the client how long
        the message is. This should not be called from the client. It
        will be called from the function _video_loop() which is on a
        parrallel thread with Pyro5.

        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")
        
        bayer = np.frombuffer(self.meminfo[0], c_ubyte).reshape(self.roi_shape[1], self.roi_shape[0])

        ow = (bayer.shape[0]//4) * 4
        oh = (bayer.shape[1]//4) * 4

        R  = bayer[0::2, 0::2]
        B  = bayer[1::2, 1::2]
        G0 = bayer[0::2, 1::2]
        G1 = bayer[1::2, 0::2]

        GRAY = R[:oh,:ow]//3 + B[:oh,:ow]//3 + (G0[:oh,:ow]//2 + G1[:oh,:ow]//2)//3

        msg = pickle.dumps(GRAY)
        msg = bytes(f'{len(msg):<{self.HEADERSIZE}}', "utf-8") + msg
        return msg

    def _video_loop(self):
        """
        This function is called as a seperate thread when streaming is initiated.
        It will loop, sending frame by frame accross the socket connection,
        until the threading.Event() stop_video is triggered.
        
        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")
        
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

        Parameters
        ----------
        clockspeed: int
            clock speed of the camera
        
        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.        
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")
        
        pixelclock = c_uint(clockspeed)
        i = tc.PixelClock(self.handle, 6, byref(pixelclock), sizeof(pixelclock))

    def start_capture(self):
        """
        This starts the capture from the camera to the allocated
        memory location as well as starts a new parallel thread
        for the socket server to stream from memory to the client.

        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")
        
        tc.StartCapture(self.handle, 1)
        self.start_socket = True
        self.stop_video = threading.Event()
        self.video_thread = threading.Thread(target=self._video_loop, args=())
        self.video_thread.start()

    def stop_capture(self):
        """
        This frees the memory used for storing the frames then triggers
        the stop_video event which will end the parrallel socket thread.

        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")
        
        tc.FreeMemory(self.handle, self.meminfo[0], self.meminfo[1])
        tc.StopCapture(self.handle, 1)
        self.clientsocket.close()
        self.stop_video.set()
        
    def initialize_memory(self, pixelbytes=8):
        """
        Initializes the memory for holding the most recent frame from the camera.

        Parameters
        ----------
        pixelbytes: int
            the amount of memory space allocated per pixel in bytes

        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")
        
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
        This sets the exposure of the camera.

        Parameters
        ----------
        exposure: int
            in milliseconds, the time the shutter is open on the camera (90 is a good exposure value)

        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")
        
        exposure_c = c_double(exposure)
        tc.SetExposure(self.handle, 12 , exposure_c, sizeof(exposure_c))
        self.exposure = exposure_c.value
    
    def set_framerate(self, framerate):
        """
        Sets the framerate of the camera (fps). After calling
        this function you must reset the exposure.

        Parameters
        ----------
        framerate: int
            the framerate of the camera in frames per second

        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """  
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")
            
        s_framerate = c_double(0)
        tc.SetFrameRate(self.handle, c_double(framerate), byref(s_framerate))
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
        Parameters
        ----------
        mode: int
            the color mode of the pixel data

        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")
        
        i = tc.SetColorMode(self.handle, mode) #11 means raw 8-bit, 6 means gray 8-bit

    def set_roi_shape(self, roi_shape):
        """
        Sets the dimmenstions of the region of interest (roi)

        Parameters
        ----------
        roi_shape : int x int
            dimentions of the image that is taken by the camera (usually 1024 x 1280)

        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")
        
        AOI_size = tc.IS_2D(roi_shape[0], roi_shape[1]) #Width and Height
            
        i = tc.AOI(self.handle, 5, byref(AOI_size), 8)#5 for setting size, 3 for setting position
        tc.AOI(self.handle, 6, byref(AOI_size), 8)#6 for getting size, 4 for getting position
        self.roi_shape = [AOI_size.s32X, AOI_size.s32Y]

    def set_roi_pos(self, roi_pos):
        """
        Sets the origin position of the region of interest

        Parameters
        ----------
        roi_pos : int x int
            position of the top left corner of the roi (region of interest) in relation to the sensor array (usaually 0,0)

        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")
        
        AOI_pos = tc.IS_2D(roi_pos[0], roi_pos[1]) #Width and Height
            
        i = tc.AOI(self.handle, 3, byref(AOI_pos), 8 )#5 for setting size, 3 for setting position
        tc.AOI(self.handle, 4, byref(AOI_pos), 8 )#6 for getting size, 4 for getting position
        self.roi_pos = [AOI_pos.s32X, AOI_pos.s32Y]

    def close(self):
        """
        Calls self.stop_capture to free memory and end the socket server
        and then closes serial communication with the camera.

        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        PyroError("Closing ThorCam failed with error code "+str(i))
            Error to signal that the connection to the camera was closed abruptly or another error was thrown upon closing (usually is ignorable)
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")
        
        try:
            self.handle
        except AttributeError:
            return
        self.stop_capture()
        i = tc.ExitCamera(self.handle) 
        if i != 0:
            raise PyroError("Closing ThorCam failed with error code "+str(i))

    def __del__(self):
        """"
        Function called when Proxy connection is lost.
        """
        self.close()
