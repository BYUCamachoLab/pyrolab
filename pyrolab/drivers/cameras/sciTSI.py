# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Thorlabs Scientific Camera
--------------------------

Driver for a Thorlabs Microscope.

Contributors
 * David Hill (https://github.com/hillda3141)
"""

from Pyro5.errors import PyroError
from pyrolab.api import expose
from thorlabs_kinesis import thor_science_camera as tc
import socket
import pickle
import time
import threading
import numpy as np
from ctypes import *

@expose
class SCICAM:
    """
    Driver for the ThorLabs SCICAM.

    Attributes
    ----------
    HEADERSIZE : int
        the size of the header used to communicate the size of the message
        (10 bytes is a safe size)
    """
    HEADERSIZE = 10

    def __init__(self, ser_no, port=2222, bit_depth=8, camera="ThorCam FS", exposure=10000):
        """
        Opens the serial communication with the Thorlabs camera.
        
        Sets some low-level values, including the bit depth and camera name.

        Parameters
        ----------
        ser_no : long
            the serial number of the camera that should be initiated
        port : int
            the port on which the socket transmits the video feed to the client
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
            position of the top left corner of the roi (region of interest) in
            relation to the sensor array (usaually 0,0)
        framerate : int
            the framerate of the camera in frames per second
        exposure: int
            in milliseconds, the time the shutter is open on the camera (90 default)
        pixelbytes: int
            the amount of memory space allocated per pixel in bytes
        """

        ser_no_list = create_string_buffer(4096)
        length = c_int(4096)
        error = tc.OpenSDK()
        error = tc.DiscoverAvailableCameras(ser_no_list,length)
        if(str(ser_no) == str(ser_no_list.value.decode()).strip()):
            self.handle = c_void_p()
            error = tc.OpenCamera(ser_no_list.value, self.handle)
        # print(self.handle)
        self.bit_depth = bit_depth
        self.camera = camera

        self.set_exposure(exposure)
        self.port = port
        height = c_int()
        error = tc.GetImageHeight(self.handle,height)
        width = c_int()
        error = tc.GetImageWidth(self.handle,width)
        self.height = int(height.value)
        self.width = int(width.value)
        self.opened = True
        print("initialized")

    def _get_image(self):
        """
        Retrieves the last frame from the memory buffer, processes
        it into a gray-scale image, and serializes it using the pickle
        library. The header is then added to inform the client how long
        the message is. This should not be called from the client. It
        will be called from the function _video_loop() which is on a
        parrallel thread with Pyro5.
        """
        image_buffer = POINTER(c_ushort)()
        frame_count = c_int()
        metadata_pointer = POINTER(c_char)()
        metadata_size_in_bytes = c_int()
        tc.GetFrameOrNull(self.handle, image_buffer, frame_count, metadata_pointer, metadata_size_in_bytes)
        # print(image_buffer)
        image_buffer._wrapper = self
        if(image_buffer):
            self.bayer = np.ctypeslib.as_array(image_buffer,shape=(self.height,self.width))
        
        if(self.color == False):
            ow = (self.bayer.shape[0]//4) * 4
            oh = (self.bayer.shape[1]//4) * 4

            R  = self.bayer[0::2, 0::2]
            B  = self.bayer[1::2, 1::2]
            G0 = self.bayer[0::2, 1::2]
            G1 = self.bayer[1::2, 0::2]

            GRAY = R[:oh,:ow]//3 + B[:oh,:ow]//3 + (G0[:oh,:ow]//2 + G1[:oh,:ow]//2)//3

            if(self.local == True):
                return GRAY
            else:
                msg = pickle.dumps(GRAY)
                msg = bytes(f'{len(msg):<{self.HEADERSIZE}}', "utf-8") + msg
                return msg
        else:
            if(self.local == True):
                return self.bayer
            else:
                msg = pickle.dumps(self.bayer)
                msg = bytes(f'{len(msg):<{self.HEADERSIZE}}', "utf-8") + msg
                return msg
            

    def _video_loop(self):
        """
        This function is called as a seperate thread when streaming is initiated.
        It will loop, sending frame by frame accross the socket connection,
        until the threading.Event() stop_video is triggered.
        """
        while not self.stop_video.is_set():
            if(self.local == False):
                if self.start_socket==True:
                    while True:
                        self.serversocket = socket.socket(socket.AF_INET,
                                                            socket.SOCK_STREAM)
                        self.serversocket.bind((socket.gethostname(), self.port))
                        self.serversocket.listen(5)
                        self.clientsocket, address = self.serversocket.accept()
                        self.start_socket = False
                        break
                msg = self._get_image()
                self.clientsocket.send(msg)
                # check_msg = self.clientsocket.recv(2)
                # if(check_msg == b'b'):
                #     break
            else:
                break
            
    def get_frame(self):
        """
        Returns the most recently updated frame from the camera. Only use if the
        program is connecting to a local camera.   
        """
        if(self.local == True):
            return self._get_image()

    def start_capture(self,color=False,local=True):
        """
        This starts the capture from the camera to the allocated
        memory location as well as starts a new parallel thread
        for the socket server to stream from memory to the client.

        Parameters
        ----------
        color : boolean
            whether the video should be sent in full color or grayscale
        """
        self.color = color
        self.local = local
        self.bayer = np.zeros((1080,1440))
        error = tc.ArmCamera(self.handle,c_int(2))
        error = tc.IssueSoftwareTrigger(self.handle)
        ip_address = socket.gethostbyname(socket.gethostname())
        self.start_socket = True
        self.stop_video = threading.Event()
        self.video_thread = threading.Thread(target=self._video_loop, args=())
        self.video_thread.start()
        return ip_address

    def stop_capture(self):
        """
        This frees the memory used for storing the frames then triggers
        the stop_video event which will end the parrallel socket thread.
        """
        
        self.stop_video.set()
        if(self.local == False):
            self.clientsocket.close()
            self.serversocket.close()
        tc.DisarmCamera(self.handle)
        
    
    def set_exposure(self, exposure):
        """
        This sets the exposure of the camera.

        Parameters
        ----------
        exposure: int
            in milliseconds, the time the shutter is open on the camera (90 is
            a good exposure value)
        """
        min_exposure = c_longlong()
        max_exposure = c_longlong()
        error = tc.GetExposureTimeRange(self.handle,min_exposure,max_exposure)
        if(exposure < min_exposure.value):
            exposure = min_exposure.value
        if(exposure > max_exposure.value):
            exposure = max_exposure.value
        exp_c = c_longlong(exposure)
        error = tc.SetExposure(self.handle,exp_c)
        # print(error)
        self.exposure = exposure

    def close(self):
        """
        Calls self.stop_capture to free memory and end the socket server
        and then closes serial communication with the camera.

        Raises
        ------
        PyroError("Closing ThorCam failed with error code "+str(i))
            Error to signal that the connection to the camera was closed abruptly
            or another error was thrown upon closing (usually is ignorable)
        """
        if(self.opened == True):
            try:
                self.handle
            except AttributeError:
                return
            self.stop_capture()
            tc.CloseCamera(self.handle)
            tc.CloseSDK()
            print("camera closed")
            self.opened = False

    def __del__(self):
        """"
        Function called when Proxy connection is lost.
        """
        self.close()
