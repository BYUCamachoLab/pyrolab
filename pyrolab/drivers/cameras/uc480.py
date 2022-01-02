# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Thorlabs UC480 Scientific Camera
================================

Driver for a Thorlabs Microscope.

.. attention::

   Presently Windows only. 
   
   Requires ThorCam software. Download it at `thorlabs.com`_.

   .. _thorlabs.com: https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=ThorCam

   Potential future Linux support, since ThorLabs does provide a Windows and 
   Linux SDK.

.. admonition:: Dependencies
   :class: note

   thorlabs_kinesis (:ref:`installation instructions <Thorlabs Kinesis Package>`)
"""

# TODO: Investigate Linux support 
# (https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=ThorCam)

import pickle
import socket
import threading
from ctypes import *
from typing import Tuple

import numpy as np
from thorlabs_kinesis import thor_camera as tc

from pyrolab.api import expose
from pyrolab.errors import PyroLabError


@expose
class UC480:
    """
    The Thorlabs UC480 camera driver.

    Attributes
    ----------
    HEADERSIZE : int
        The size of the header used to communicate the size of the message
        (10 bytes is a safe size)
    """
    HEADERSIZE = 10

    def connect(self, serialno, port=2222, bit_depth=8, camera="ThorCam FS",
                 pixel_clock=24, color_mode=11, roi_shape=(1024, 1280), 
                 roi_pos=(0,0), framerate=15, exposure=90, pixelbytes=8):
        """
        Opens the serial communication with the Thorlabs camera and sets defaults.
        
        Default low-level values that are set include the bit depth and camera 
        name.

        Parameters
        ----------
        serialno : int
            The serial number of the camera that should be connected.
        port : int, optional
            The port on which the socket transmits the video feed to the client.
        bit_depth : int, optional
            The number of bits used for each pixel (default 8).
        camera: string, optional
            Camera name (default "ThorCam FS").
        pixel_clock: int, optional
            Clock speed of the camera (default 24).
        color_mode: int, optional
            Mode of color that the camera returns data in. ``11`` (default) 
            returns raw format, see :py:func:`set_color_mode` for more 
            information.
        roi_shape : tuple(int, int), optional
            Dimensions of the image that is taken by the camera (default 
            ``(1024, 1280)``).
        roi_pos : tuple(int, int), optional
            Position of the top left corner of the roi (region of interest) in
            relation to the sensor array (default ``(0,0)``).
        framerate : int, optional
            The framerate of the camera in frames per second (default 15).
        exposure: int, optional
            In milliseconds, the time the shutter is open on the camera 
            (default 90).
        pixelbytes: int, optional
            The amount of memory space allocated per pixel in bytes (default 8).
        """
        num = c_int(0)
        tc.GetNumberOfCameras(byref(num))
        print(num)
        uci_format = tc.UC480_CAMERA_INFO * 2
        uci = uci_format(tc.UC480_CAMERA_INFO(), tc.UC480_CAMERA_INFO())
        dwCount = c_int(num.value)
        cam_list = tc.UC480_CAMERA_LIST(dwCount=dwCount,uci=uci)
        tc.GetCameraList(byref(cam_list))
        for i in range(num.value):
            handle = c_int(cam_list.uci[i].dwCameraID)
            temp = tc.InitCamera(byref(handle))
            if(temp != 0):
                continue
            info = tc.CAMINFO()
            out = tc.GetCameraInfo(handle,byref(info))
            if(int(info.SerNo) == serialno):
                self.handle = handle
                break
            elif(i == num.value - 1):
                raise PyroLabError("Camera not found")
            else:
                i = tc.ExitCamera(handle)
                if i != 0:
                    raise PyroLabError("Closing ThorCam failed with error code "+str(i))

        self.bit_depth = bit_depth
        self.camera = camera

        #print("Trigger Mode: " + str(tc.SetTrigger(handle,tc.IS_SET_TRIGGER_SOFTWARE)))
        print("Trigger Mode: " + str(tc.SetTrigger(self.handle,tc.IS_GET_EXTERNALTRIGGER)))
   
        tc.SetDisplayMode(self.handle, c_int(32768))

        # if i  0:
        #     print("shee")
        #     raise PyroLabError("Opening the ThorCam failed with error code "+str(i))

        self.meminfo = None

        self.set_pixel_clock(pixel_clock)
        self.set_color_mode(color_mode)
        self.set_roi_shape(roi_shape)
        self.set_roi_pos(roi_pos)
        self.set_framerate(framerate)
        self.set_exposure(exposure)
        self.initialize_memory(pixelbytes)  
        self.port = port
        print("initialized")

    def _get_image(self):
        """
        Retrieves the last frame from the memory buffer.
        
        Retrieves the last frame from the memory buffer, processes
        it into a gray-scale image, and serializes it using the pickle
        library. The header is then added to inform the client how long
        the message is. This should not be called from the client. It
        will be called from the function _video_loop() which is on a
        parallel thread with Pyro5.
        """
        bayer = np.frombuffer(self.meminfo[0], c_ubyte).reshape(self.roi_shape[1],
        self.roi_shape[0])
        
        if(self.color == False):
            ow = (bayer.shape[0]//4) * 4
            oh = (bayer.shape[1]//4) * 4

            R  = bayer[0::2, 0::2]
            B  = bayer[1::2, 1::2]
            G0 = bayer[0::2, 1::2]
            G1 = bayer[1::2, 0::2]

            GRAY = R[:oh,:ow]//3 + B[:oh,:ow]//3 + (G0[:oh,:ow]//2 + G1[:oh,:ow]//2)//3

            if(self.local == True):
                return GRAY
            else:
                msg = pickle.dumps(GRAY)
                msg = bytes(f'{len(msg):<{self.HEADERSIZE}}', "utf-8") + msg
                return msg
        else:
            if(self.local == True):
                return bayer
            else:
                msg = pickle.dumps(bayer)
                msg = bytes(f'{len(msg):<{self.HEADERSIZE}}', "utf-8") + msg
                return msg
            

    def _video_loop(self):
        """
        Starts a separate thread to stream frames.

        This function is called as a seperate thread when streaming is initiated.
        It will loop, sending frame by frame accross the socket connection,
        until the threading.Event() stop_video is triggered.
        """
        while not self.stop_video.is_set():
            bad = False
            if(self.local == False):
                if bad == False:
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
                    while True:
                        check_msg = self.clientsocket.recv(2)
                        if(check_msg == b'b'):
                            bad = True
                        break
            else:
                break
            
    def get_frame(self):
        """
        Gets the most recently updated frame.

        Returns the most recently updated frame from the camera. Only use if the
        program is connecting to a local camera.   
        """
        if(self.local == True):
            return self._get_image()

        
    def set_pixel_clock(self, clockspeed: int) -> None:
        """
        Sets the clockspeed of the camera, usually in the range of 24.

        Parameters
        ----------
        clockspeed : int
            clock speed of the camera       
        """

        pixelclock = c_uint(clockspeed)
        i = tc.PixelClock(self.handle, 6, byref(pixelclock), sizeof(pixelclock))

    def start_capture(self, color: bool = False, local: bool = True) -> str:
        """
        Starts capture from the camera.

        This starts the capture from the camera to the allocated
        memory location as well as starts a new parallel thread
        for the socket server to stream from memory to the client.

        Parameters
        ----------
        color : bool, optional
            Whether the video should be sent in full color or grayscale
            (default False).
        local : bool
            Whether the video should be sent to the local computer or to the
            client (default True).

        Returns
        -------
        ip_address : str
            The delivery IP address of the video stream.
        """
        self.color = color
        self.local = local
        tc.StartCapture(self.handle, tc.IS_DONT_WAIT)
        ip_address = socket.gethostbyname(socket.gethostname())
        self.start_socket = True
        self.stop_video = threading.Event()
        self.video_thread = threading.Thread(target=self._video_loop, args=())
        self.video_thread.start()
        return ip_address
    
    def color_gray(self, color: bool = False) -> None:
        """
        Sets the color of the video.

        This function switches whether the socket transmits color or grayscale.
        
        Parameters
        ----------
        color : boolean
            Whether the video should be sent in full color or grayscale
            (default False).
        """
        self.color = color

    def stop_capture(self) -> None:
        """
        Stops the capture from the camera.

        This frees the memory used for storing the frames then triggers
        the stop_video event which will end the parrallel socket thread.
        """
        tc.FreeMemory(self.handle, self.meminfo[0], self.meminfo[1])
        tc.StopCapture(self.handle, 1)
        if(self.local == False):
            self.clientsocket.close()
        self.stop_video.set()
        
    def initialize_memory(self, pixelbytes: int = 8) -> None:
        """
        Initializes the memory for holding the most recent frame from the camera.

        Parameters
        ----------
        pixelbytes: int, optional
            The amount of memory space allocated per pixel in bytes (default 8).
        """
        
        if self.meminfo != None:
            tc.FreeMemory(self.handle, self.meminfo[0], self.meminfo[1])
        
        xdim = self.roi_shape[0]
        ydim = self.roi_shape[1]
        imagesize = xdim*ydim
            
        memid = c_int(0)
        c_buf = (c_ubyte * imagesize)(0)

        tc.AllocateMemory(self.handle, xdim, ydim, c_int(pixelbytes), c_buf,
                          byref(memid))
        tc.SetImageMemory(self.handle, c_buf, memid)
        self.meminfo = [c_buf, memid]
    
    def set_exposure(self, exposure: int = 90) -> None:
        """
        Sets the exposure of the camera.

        90 milliseconds is a good default.

        Parameters
        ----------
        exposure: int, optional
            The time the shutter is open on the camera in milliseconds 
            (default 90).
        """
        
        exposure_c = c_double(exposure)
        tc.SetExposure(self.handle, 12 , exposure_c, sizeof(exposure_c))
        self.exposure = exposure_c.value
    
    def set_framerate(self, framerate: int) -> None:
        """
        Sets the framerate of the camera (fps). 
        
        After calling this function you must reset the exposure.

        Parameters
        ----------
        framerate: int
            The framerate of the camera in frames per second.
        """
            
        s_framerate = c_double(0)
        tc.SetFrameRate(self.handle, c_double(framerate), byref(s_framerate))
        self.framerate = s_framerate.value

    def set_color_mode(self, mode: int = 11) -> None:
        """
        Sets the color mode of the image.

        This sets the mode of image that is taken. Almost always
        use ``11`` which will give you the raw photosensor data in the format:

        .. table::

           +----+----+----+
           | R  | G0 |... |
           +----+----+----+
           | G1 | B  |... |
           +----+----+----+
           |... |... |    |
           +----+----+----+
        
        This data is interpreted in the _get_image() function.

        Parameters
        ----------
        mode : int, optional
            The color mode of the pixel data. ``11``, the default, means raw 
            8-bit. ``6`` means gray 8-bit.
        """        
        i = tc.SetColorMode(self.handle, mode)

    def set_roi_shape(self, roi_shape: Tuple[int, int]):
        """
        Sets the dimensions of the region of interest (roi).

        Parameters
        ----------
        roi_shape : tuple(int, int)
            Dimensions of the image that is taken by the camera 
            (usually 1024 x 1280).
        """
        
        AOI_size = tc.IS_2D(roi_shape[0], roi_shape[1]) #Width and Height
            
        i = tc.AOI(self.handle, 5, byref(AOI_size), 8)#5 for setting size,
                                                      #3 for setting position
        tc.AOI(self.handle, 6, byref(AOI_size), 8)#6 for getting size
                                                  #4 for getting position
        self.roi_shape = [AOI_size.s32X, AOI_size.s32Y]

    def set_roi_pos(self, roi_pos: Tuple[int, int]) -> None:
        """
        Sets the origin position of the region of interest.

        Parameters
        ----------
        roi_pos : tuple(int, int)
            Position of the top left corner of the roi (region of interest) in
            relation to the sensor array (usually ``(0,0)``).
        """
        
        AOI_pos = tc.IS_2D(roi_pos[0], roi_pos[1]) #Width and Height
            
        i = tc.AOI(self.handle, 3, byref(AOI_pos), 8 )#5 for setting size
                                                      #3 for setting position
        tc.AOI(self.handle, 4, byref(AOI_pos), 8 )#6 for getting size
                                                  #4 for getting position
        self.roi_pos = [AOI_pos.s32X, AOI_pos.s32Y]

    def close(self):
        """
        Closes communication with the camera and frees memory.

        Calls :py:func:`stop_capture` to free memory and end the socket server
        and then closes serial communication with the camera.

        Raises
        ------
        PyroLabError
            Error to signal that the connection to the camera was closed 
            abruptly or another error was thrown upon closing (usually 
            safely ignorable).
        """
        
        try:
            self.handle
        except AttributeError:
            return
        self.stop_capture()
        i = tc.ExitCamera(self.handle) 
        if i != 0:
            raise PyroLabError("Closing ThorCam failed with error code "+str(i))
