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

import logging
import pickle
import socket
import threading
from ctypes import *
from typing import Tuple

import numpy as np
try:
    from thorlabs_kinesis import thor_camera as tc
except:
    pass
from Pyro5.api import locate_ns, Proxy

from pyrolab.api import expose
from pyrolab.drivers.cameras import Camera
from pyrolab.errors import PyroLabError


log = logging.getLogger(__name__)


@expose
class UC480(Camera):
    """
    The Thorlabs UC480 camera driver.

    Attributes
    ----------
    HEADERSIZE : int
        The size of the header used to communicate the size of the message
        (10 bytes is a safe size)
    color : bool
        Whether the camera is in color mode or not. If False, images and video
        will be transmitted in grayscale.
    """
    HEADERSIZE = 10

    def __init__(self):
        self.stop_video = threading.Event()
        self.color = True

    def connect(self, serialno, local: bool = False, bit_depth=8,
                 pixel_clock=24, color: bool = True, color_mode=11, roi_shape=(1024, 1280), 
                 roi_pos=(0,0), framerate=15, exposure=90, pixelbytes=8, brightness: int = 5):
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
        pixel_clock: int, optional
            Clock speed of the camera (default 24).
        color : bool, optional
            Whether the camera is in color mode or not (default True).
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
        brightness : int
            Integer (range 1-10) defining the brightness, where 5 leaves the 
            brightness unchanged.
        """
        self.local = local
        log.debug(f"Attempting to connect to camera with serialno '{serialno}'")
        num = c_int(0)
        tc.GetNumberOfCameras(byref(num))
        log.debug(f"Number of cameras found: {num.value}")

        uci_format = tc.UC480_CAMERA_INFO * 2
        uci = uci_format(tc.UC480_CAMERA_INFO(), tc.UC480_CAMERA_INFO())
        dwCount = c_int(num.value)
        cam_list = tc.UC480_CAMERA_LIST(dwCount=dwCount,uci=uci)
        tc.GetCameraList(byref(cam_list))

        # Find the camera with the given serial number. Each camera has to be
        # connected to and asked its serial number. We then check that they
        # match.
        for i in range(num.value):
            handle = c_int(cam_list.uci[i].dwCameraID)
            error = tc.InitCamera(byref(handle))
            
            # 0 means no error
            if(error != 0):
                continue

            info = tc.CAMINFO()
            error = tc.GetCameraInfo(handle, byref(info))

            if(int(info.SerNo) == serialno):
                self.handle = handle
                break
            elif(i == num.value - 1):
                raise PyroLabError("Camera not found")
            else:
                error = tc.ExitCamera(handle)
                if error != 0:
                    log.critical(f"Closing ThorCam failed with error code {error}")

        self.bit_depth = bit_depth

        #print("Trigger Mode: " + str(tc.SetTrigger(handle,tc.IS_SET_TRIGGER_SOFTWARE)))
        log.debug("Trigger mode: " + str(tc.SetTrigger(self.handle, tc.IS_GET_EXTERNALTRIGGER)))
   
        tc.SetDisplayMode(self.handle, c_int(32768))

        self.meminfo = None

        self.set_pixel_clock(pixel_clock)
        self.set_color_mode(color_mode)
        self.set_roi_shape(roi_shape)
        self.set_roi_pos(roi_pos)
        self.set_framerate(framerate)
        self.set_exposure(exposure)
        self._initialize_memory(pixelbytes)
        self.brightness = brightness
    
    def _bayer_convert(self, bayer: np.array) -> np.array:
        """
        Coverts the raw data to something that can be displayed on-screen.

        Image data is retrieved as a single-dimensional array. This function 
        converts it into either multidimensional BGR or grayscale image.

        Parameters
        ----------
        bayer : np.array
            The raw data that is received from the camera.

        Returns
        -------
        np.array
            The converted data.
        """

        if self.color:
            log.debug("entered color")
            frame_height = bayer.shape[0]//2
            frame_width = bayer.shape[1]//2

            ow = (bayer.shape[0]//4) * 4
            oh = (bayer.shape[1]//4) * 4

            R  = bayer[0::2, 0::2]
            B  = bayer[1::2, 1::2]
            G0 = bayer[0::2, 1::2]
            G1 = bayer[1::2, 0::2]
            G = G0[:oh,:ow]//2 + G1[:oh,:ow]//2

            bayer_R = np.array(R, dtype=np.uint8).reshape(frame_height, frame_width)
            bayer_G = np.array(G, dtype=np.uint8).reshape(frame_height, frame_width)
            bayer_B = np.array(B, dtype=np.uint8).reshape(frame_height, frame_width)

            log.debug("stacking color data...")

            dStack = np.clip(np.dstack((bayer_B*(self.brightness/5),bayer_G*(self.brightness/5),
                            bayer_R*(self.brightness/5))),0,np.power(2,self.bit_depth)-1).astype('uint8')
            
            log.debug("data stacked")
        else:
            frame_height = bayer.shape[0]
            frame_width = bayer.shape[1]
            bayer_T = np.array(bayer, dtype=np.uint8).reshape(frame_height,
                            frame_width)

            dStack = np.clip(np.dstack(((bayer_T)*(self.brightness/5))),0,
                            np.power(2,self.bit_depth)-1).astype('uint8')
        return dStack

    def get_frame(self) -> list:
        """
        Retrieves the last frame from the camera's memory buffer.

        Retrieves the last frame from the camera memory buffer and processes it
        into a computer-readable image format.

        For remote connections, the image is serialized using the pickle module
        for remote connections. The header is then added to inform the client
        how long the message is. This should not be called from the client. It
        will be called from the function _video_loop() which is on a parallel
        thread with Pyro5.

        Can only be called after :py:func:`start_capture`.

        Returns
        -------
        np.array
            The last frame from the camera's memory buffer.
        """
        log.debug("Retreiving frame from memory...")
        raw = np.frombuffer(self.meminfo[0], c_ubyte).reshape(self.roi_shape[1],
        self.roi_shape[0])
        log.debug(f"Retreived {len(raw)}")
        
        if(self.color == False):
            ow = (raw.shape[0]//4) * 4
            oh = (raw.shape[1]//4) * 4

            R  = raw[0::2, 0::2]
            B  = raw[1::2, 1::2]
            G0 = raw[0::2, 1::2]
            G1 = raw[1::2, 0::2]

            raw = R[:oh,:ow]//3 + B[:oh,:ow]//3 + (G0[:oh,:ow]//2 + G1[:oh,:ow]//2)//3

        img = self._bayer_convert(raw)
        log.debug("bayer done")
        return img

    def _remote_streaming_loop(self):
        """
        Starts a separate thread to stream frames.

        This function is called as a seperate thread when streaming is initiated.
        It will loop, sending frame by frame accross the socket connection,
        until the threading.Event() stop_video is triggered.
        """
        log.debug("Waiting for client to connect...")
        self.serversocket.listen(5)
        self.clientsocket, address = self.serversocket.accept()
        log.debug("Accepted client socket")
        
        while not self.stop_video.is_set():
            log.debug("Getting frame...")
            msg = self.get_frame()
            log.debug("Serializing...")
            ser_msg = pickle.dumps(msg)
            ser_msg = bytes(f'{len(ser_msg):<{self.HEADERSIZE}}', "utf-8") + ser_msg
            log.debug("Sending message...")
            self.clientsocket.send(ser_msg)
            log.debug("Message sent")
            check_msg = self.clientsocket.recv(4096)
            log.debug("Ack")
            

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

    def start_capture(self, local: bool = True) -> Tuple[str, str]:
        """
        Starts capture from the camera.

        This starts the capture from the camera to the allocated
        memory location as well as starts a new parallel thread
        for the socket server to stream from memory to the client.

        Parameters
        ----------
        local : bool
            Whether the video should be sent to the local computer or to the
            client (default True).

        Returns
        -------
        address, port : tuple(str, str)
            The delivery IP address and port of the video stream.
        """
        tc.StartCapture(self.handle, tc.IS_DONT_WAIT)
        if not self.local:
            self.stop_video.clear()
            address = socket.gethostbyname(socket.gethostname())
            self.serversocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self.serversocket.bind((socket.gethostname(), 0))
            port = self.serversocket.getsockname()[1]
            self.video_thread = threading.Thread(target=self._remote_streaming_loop, args=())
            self.video_thread.start()
            return [address,port]

    def stop_capture(self) -> None:
        """
        Stops the capture from the camera.

        This frees the memory used for storing the frames then triggers
        the stop_video event which will end the parrallel socket thread.
        """
        tc.FreeMemory(self.handle, self.meminfo[0], self.meminfo[1])
        tc.StopCapture(self.handle, 1)
        if not self.local:
            self.clientsocket.close()
        self.stop_video.set()
        
    def _initialize_memory(self, pixelbytes: int = 8) -> None:
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
        error = tc.ExitCamera(self.handle) 
        if error != 0:
            log.critical(f"Closing ThorCam failed (code {error})")


class UC480Client():
    """
    The Thorlabs UC480 camera driver.

    Parameters
    ----------
    HEADERSIZE : int
        The size of the header used to communicate the size of the message
        (10 bytes is a safe size)
    SUB_MESSAGE_LENGTH : int
        The size of the sub-message chunks used.
    """
    def __init__(self, HEADERSIZE: int = 10, SUB_MESSAGE_LENGTH: int = 4096):
        self.HEADERSIZE = HEADERSIZE
        self.SUB_MESSAGE_LENGTH = SUB_MESSAGE_LENGTH
        self.stop_video = threading.Event()

    def connect(self, name: str) -> None:
        """
        Connect to a remote PyroLab-hosted UC480 camera.

        Assumes the nameserver where the camera is registered is already 
        configured in the environment.

        Parameters
        ----------
        name : str
            The name used to register the camera on the nameserver.
        """
        ns = locate_ns()
        self.cam = Proxy(ns.lookup(name))
        self.cam.autoconnect()
    
    def start_video(self, color: bool=True, brightness: int=5) -> None:
        address, port = self.cam.start_capture()
        self.clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clientsocket.connect((address, port))
        self.stop_video.clear()
        self.video_thread = threading.Thread(target=self._receive_video_loop, args=())
        self.video_thread.start()

    def set_color(self, color: bool=True) -> None:
        self.cam.set_color(color)
    
    def set_brightness(self, brightness: int=5) -> None:
        self.cam.set_brightness(brightness)
    
    def _receive_video_loop(self) -> None:
        while not self.stop_video.is_set():
            msg = b''
            new_msg = True
            msg_len = None
            image = None
            while True:
                if new_msg:
                    sub_msg = self.clientsocket.recv(self.HEADERSIZE) #read size of the message
                    msg_len = int((sub_msg[:self.HEADERSIZE]))
                    new_msg = False
                else:
                    sub_msg = self.clientsocket.recv(self.SUB_MESSAGE_LENGTH)
                    msg += sub_msg
                    if len(msg) == msg_len: #once the whole messge is received
                        image = pickle.loads(msg)  #deserialize the message and break
                        self.clientsocket.send(b'ak')  
                        break
            self.dStack = image
        self.clientsocket.close()

    
    def end_video(self) -> None:
        self.stop_video.set()
        self.cam.stop_capture()

    def get_frame(self):
        return self.dStack

    def close(self) -> None:
        self.cam.close()
