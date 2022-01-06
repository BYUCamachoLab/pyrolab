# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
ThorCam
=======

Module providing basic functionality for Thorlabs cameras.

Provides a base class with common functionality for Thorlabs cameras. Not 
intended to be instantiated directly, even if it works.

Driver for ThorLabs cameras interfacing with the ThorCam software DLLs.

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

import logging
import pickle
import socket
import threading
import time
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


class ThorCamBase(Camera):
    """
    The Thorlabs UC480 camera driver.

    Attributes
    ----------
    HEADERSIZE : int
        The size in bytes of the header in each serialized message (read only).
    pixelclock : int
    exposure : int
    framerate : int
    brightness : int
    color : bool
    """
    def __init__(self):
        self._HEADERSTRUCT = np.zeros(4, dtype=np.uint32)
        self.stop_video = threading.Event()
        self.VIDEO_THREAD_READY = False

        self.brightness = 5
        self.color = True

    @property
    @expose
    def HEADERSIZE(self) -> int:
        return self._HEADERSTRUCT.itemsize * self._HEADERSTRUCT.size

    @property
    @expose
    def pixelclock(self) -> int:
        """Sets the clockspeed of the camera, usually in the range of 24."""
        return self._pixelclock

    @pixelclock.setter
    @expose
    def pixelclock(self, clockspeed: int) -> None:
        self._pixelclock = clockspeed
        pixelclock = c_uint(clockspeed)
        if hasattr(self, "handle"):
            tc.PixelClock(self.handle, 6, byref(pixelclock), sizeof(pixelclock))
        else:
            raise PyroLabError("Cannot set pixelclock before connecting to device.")

    @property
    @expose
    def exposure(self) -> int:
        """Sets the exposure of the camera, the time the shutter is open in
        milliseconds (90 ms is a good default)."""
        return self._exposure

    @exposure.setter
    @expose
    def exposure(self, exposure: int) -> None:
        self._exposure = exposure
        exposure_c = c_double(exposure)
        if hasattr(self, "handle"):
            tc.SetExposure(self.handle, 12 , exposure_c, sizeof(exposure_c))
        else:
            raise PyroLabError("Cannot set exposure before connecting to device.")

    @property
    @expose
    def framerate(self) -> int:
        """The framerate of the camera (fps). You must reset the exposure
        after setting the framerate."""
        return self._framerate

    @framerate.setter
    @expose
    def framerate(self, framerate: int) -> None:
        self._framerate = framerate
        s_framerate = c_double(0)
        if hasattr(self, "handle"):
            tc.SetFrameRate(self.handle, c_double(framerate), byref(s_framerate))
        else:
            raise PyroLabError("Cannot set framerate before connecting to device.")

    @property
    @expose
    def brightness(self) -> int:
        """Integer (range 1-10) defining the brightness, where 5 leaves the
        brightness unchanged."""
        return self._brightness

    @brightness.setter
    @expose
    def brightness(self, brightness: int) -> None:
        self._brightness = brightness

    @property
    @expose
    def color(self) -> bool:
        """Sets whether to transmit color (``True``) or grayscale (``False``) 
        images."""
        return self._color

    @color.setter
    @expose
    def color(self, color: bool) -> None:
        self._color = color

    @property
    @expose
    def roi_shape(self) -> list:
        """Sets whether to transmit color (``True``) or grayscale (``False``) 
        images."""
        return self._software_roi_shape

    @roi_shape.setter
    @expose
    def roi_shape(self, shape: list) -> None:
        self._software_roi_shape = shape

    @property
    @expose
    def roi_pos(self) -> list:
        """Sets whether to transmit color (``True``) or grayscale (``False``) 
        images."""
        return self._software_roi_pos

    @roi_pos.setter
    @expose
    def roi_pos(self, pos: list) -> None:
        self._software_roi_pos = pos

    @expose
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
        tc.SetColorMode(self.handle, mode)

    @expose
    def connect(self, 
                serialno: str, 
                local: bool = False, 
                bit_depth: int = 8,
                pixelclock: int = 24, 
                color: bool = True, 
                colormode: int = 11, 
                roi_shape: Tuple[int, int] = (1024, 1280), 
                roi_pos: Tuple[int, int] = (0,0), 
                framerate: int = 15, 
                exposure: int = 90, 
                pixelbytes: int = 8, 
                brightness: int = 5
    ):
        """
        Opens the serial communication with the Thorlabs camera and sets defaults.
        
        Default low-level values that are set include the bit depth and camera 
        name.

        Parameters
        ----------
        serialno : int
            The serial number of the camera that should be connected.
        bit_depth : int, optional
            The number of bits used for each pixel (default 8).
        pixelclock: int, optional
            Clock speed of the camera (default 24).
        color : bool, optional
            Whether the camera is in color mode or not (default True).
        colormode: int, optional
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
        self.color = color

        log.debug(f"Attempting to connect to camera with serialno '{serialno}'")
        num = c_int(0)
        tc.GetNumberOfCameras(byref(num))
        log.debug(f"Found {num.value} cameras")

        uci_format = tc.UC480_CAMERA_INFO * 2
        uci = uci_format(tc.UC480_CAMERA_INFO(), tc.UC480_CAMERA_INFO())
        dwCount = c_int(num.value)
        cam_list = tc.UC480_CAMERA_LIST(dwCount=dwCount, uci=uci)
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
                    log.error(f"Closing ThorCam failed with error code {error}")

        self.bit_depth = bit_depth

        #print("Trigger Mode: " + str(tc.SetTrigger(handle,tc.IS_SET_TRIGGER_SOFTWARE)))
        log.debug("Trigger mode: " + str(tc.SetTrigger(self.handle, tc.IS_GET_EXTERNALTRIGGER)))
   
        tc.SetDisplayMode(self.handle, c_int(32768))

        self.meminfo = None

        self.pixelclock = pixelclock
        self.framerate = framerate
        self.exposure = exposure
        self.brightness = brightness
        self.set_color_mode(colormode)
        log.debug("setting roi shape...")
        self._set_hardware_roi_shape(roi_shape)
        self.roi_shape = [512,640]
        log.debug("roi shape set")
        self._set_hardware_roi_pos(roi_pos)
        self.roi_pos = [0,0]
        log.debug("roi position set")
        self._initialize_memory(pixelbytes)
        log.debug("memory initialized")

    def _obtain_roi(self, image: np.array) -> np.array:
        log.debug(f"shape of image: {image.shape}")
        log.debug(f"shape: {self.roi_shape}")
        log.debug(f"positions: {self.roi_pos}")
        if self.color:
            image = image[self.roi_pos[0]:self.roi_pos[0]+self.roi_shape[0],self.roi_pos[1]:self.roi_pos[1]+self.roi_shape[1],:]
            return image
        else:
            image = image[self.roi_pos[0]:self.roi_pos[0]+self.roi_shape[0],self.roi_pos[1]:self.roi_pos[1]+self.roi_shape[1]]
        log.debug(f"new shape of image: {image.shape}")
        return image
    
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
            log.debug("Bayer convert (color)")
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

            log.debug("Stacking color data")
            dStack = np.clip(
            np.dstack(
                    (bayer_B*(self.brightness/5), bayer_G*(self.brightness/5), bayer_R*(self.brightness/5))
                ),
                0,
                np.power(2, self.bit_depth) - 1
            ).astype('uint8')
        else:
            log.debug("Bayer convert (grayscale)")
            frame_height = bayer.shape[0]
            frame_width = bayer.shape[1]
            bayer_T = np.array(bayer, dtype=np.uint8).reshape(frame_height,
                            frame_width)

            log.debug("Stacking grayscale data")
            dStack = np.clip(
                bayer_T*(self.brightness/5),
                0,
                np.power(2, self.bit_depth) - 1,
            ).astype('uint8')
        log.debug("Bayer data stacked")
        return dStack

    def get_frame(self) -> np.array:
        """
        Retrieves the last frame from the camera's memory buffer.

        Retrieves the last frame from the camera memory buffer and processes it
        into a computer-readable image format.

        .. warning:: 

           Not a Pyro exposed function, cannot be called from a Proxy. We 
           recommend using the :py:class:`ThorCamClient` for streaming 
           video/getting remote images.

        For remote connections, the image is serialized using the pickle module
        for remote connections. The header is then added to inform the client
        how long the message is. This should not be called from the client. It
        will be called from the function _video_loop() which is on a parallel
        thread with Pyro5.

        Can only be called after :py:func:`start_capture`.

        Returns
        -------
        img : np.array
            The last frame from the camera's memory buffer.
        """
        log.debug("Retreiving frame from memory")
        raw = np.frombuffer(self.meminfo[0], c_ubyte).reshape(self.hardware_roi_shape[1], self.hardware_roi_shape[0])
        log.debug(f"Retreived (len {len(raw)})")
        
        if not self.color:
            ow = (raw.shape[0]//4) * 4
            oh = (raw.shape[1]//4) * 4

            R  = raw[0::2, 0::2]
            B  = raw[1::2, 1::2]
            G0 = raw[0::2, 1::2]
            G1 = raw[1::2, 0::2]

            raw = R[:oh,:ow]//3 + B[:oh,:ow]//3 + (G0[:oh,:ow]//2 + G1[:oh,:ow]//2)//3

        bayer =  self._bayer_convert(raw)
        return self._obtain_roi(bayer)

    def _write_header(self, size: int, d1: int = 1, d2: int = 1, d3: int = 1) -> np.array:
        log.debug(f"Received: {size} {d1} {d2} {d3}")
        return np.array((size, d1, d2, d3), dtype=np.uintc)

    def _remote_streaming_loop(self):
        """
        Starts a separate thread to stream frames.

        This function is called as a seperate thread when streaming is initiated.
        It will loop, sending frame by frame accross the socket connection,
        until the ``stop_video`` is set (by :py:func:`stop_capture`).

        Sends a single image and waits for ACK before sending the next image.
        """
        log.debug("Waiting for client to connect...")
        self.serversocket.listen(5)
        self.clientsocket, address = self.serversocket.accept()
        log.debug("Accepted client socket")
        
        while not self.stop_video.is_set():
            log.debug("Getting frame")
            msg = self.get_frame()

            log.debug("Serializing")
            # ser_msg = pickle.dumps(msg)
            ser_msg = msg.tobytes()
            header = self._write_header(len(ser_msg), *msg.shape)
            # ser_msg = bytes(f'{len(ser_msg):<{self.HEADERSIZE}}', "utf-8") + ser_msg
            ser_msg = header.tobytes() + ser_msg

            log.debug(f"Sending message ({len(ser_msg)} bytes)")
            self.clientsocket.send(ser_msg)
            log.debug("Message sent")

            check_msg = self.clientsocket.recv(4096)
            log.debug(f"ACK: {check_msg}")

    def _get_socket(self) -> Tuple[str, int]:
        """
        Opens an socket on the local machine using an available port and binds to it. 

        Returns
        -------
        address, port : Tuple[str, int]
            The address and port of the new socket.
        """
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversocket.bind((socket.gethostname(), 0))
        return self.serversocket.getsockname()

    @expose
    def start_capture(self) -> Tuple[str, str]:
        """
        Starts capture from the camera.

        This starts the capture from the camera to the allocated memory
        location as well as starts a new thread for the socket server to stream
        video from camera memory to the client.

        Returns
        -------
        address, port : tuple(str, str) 
            The IP address and port of the socket serving the video stream.
        """
        log.debug("Sending signal to camera to start capture")
        tc.StartCapture(self.handle, tc.IS_DONT_WAIT)
        log.debug("Signal sent")

        if not self.local:
            log.debug("Setting up socket for streaming")
            self.stop_video.clear()
            address, port = self._get_socket()
            self.video_thread = threading.Thread(target=self._remote_streaming_loop, args=())
            # self.video_thread.daemon = True
            self.video_thread.start()
            return [address, port]

    @expose
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
        self.VIDEO_THREAD_READY = False
        
    def _initialize_memory(self, pixelbytes: int = 8) -> None:
        """
        Initializes the memory for holding the most recent frame from the camera.

        Parameters
        ----------
        pixelbytes: int, optional
            The amount of memory space allocated per pixel in bytes (default 8).
        """
        if self.meminfo is not None:
            tc.FreeMemory(self.handle, self.meminfo[0], self.meminfo[1])
        
        xdim, ydim = self.hardware_roi_shape
        log.debug(f"got dimenstions: {self.hardware_roi_shape}")
        # ydim = self.roi_shape[1]
        imgsize = xdim * ydim
        log.debug(f"image size is {imgsize}")
            
        memid = c_int(0)
        c_buf = (c_ubyte * imgsize)(0)
        log.debug("allocating memory...")
        tc.AllocateMemory(self.handle, xdim, ydim, c_int(pixelbytes), c_buf, byref(memid))
        log.debug("setting image memory...")
        tc.SetImageMemory(self.handle, c_buf, memid)
        log.debug("setting infor...")
        self.meminfo = [c_buf, memid]
        log.debug("meminfo set")

    def _set_hardware_roi_shape(self, roi_shape: Tuple[int, int]) -> None:
        """
        Sets the dimensions of the region of interest (roi).

        Parameters
        ----------
        roi_shape : tuple(int, int)
            Dimensions of the image that is taken by the camera 
            (usually 1024 x 1280).
        """
        # Width and height
        AOI_size = tc.IS_2D(roi_shape[0], roi_shape[1])
        
        # 5 for setting size, 3 for setting position
        tc.AOI(self.handle, 5, byref(AOI_size), 8)
        
        # 6 for getting sizse, 4 for getting position
        tc.AOI(self.handle, 6, byref(AOI_size), 8)
        
        self.hardware_roi_shape = [AOI_size.s32X, AOI_size.s32Y]

    def _set_hardware_roi_pos(self, roi_pos: Tuple[int, int]) -> None:
        """
        Sets the origin position of the region of interest.

        Parameters
        ----------
        roi_pos : tuple(int, int)
            Position of the top left corner of the roi (region of interest) in
            relation to the sensor array (usually ``(0,0)``).
        """
        # Width and height
        AOI_pos = tc.IS_2D(roi_pos[0], roi_pos[1])
        
        # 5 for setting size, 3 for setting position
        tc.AOI(self.handle, 3, byref(AOI_pos), 8 )

        # 6 for getting size, 4 for getting position
        tc.AOI(self.handle, 4, byref(AOI_pos), 8 )

        self.hardware_roi_pos = [AOI_pos.s32X, AOI_pos.s32Y]

    @expose
    def close(self):
        """
        Closes communication with the camera and frees memory.

        Calls :py:func:`stop_capture` to free memory and end the socket server
        and then closes serial communication with the camera.
        """
        # Raises
        # ------
        # PyroLabError
        #     Error to signal that the connection to the camera was closed 
        #     abruptly or another error was thrown upon closing (usually 
        #     safely ignorable).
        try:
            self.handle
        except AttributeError:
            return

        self.stop_capture()

        error = tc.ExitCamera(self.handle) 
        if error != 0:
            log.error(f"Closing ThorCam failed (code {error})")


class ThorCamClient:
    """
    The Thorlabs UC480 camera driver. Not a PyroLab :py:class:`Service` object.

    Any :py:class:`ThorCamBase` attribute is a valid ThorCamClient attribute.

    Attributes
    ----------
    SUB_MESSAGE_LENGTH : int
        The size of the sub-message chunks used.
    """
    def __init__(self):
        self.remote_attributes = []
        self.SUB_MESSAGE_LENGTH = 4096
        self.stop_video = threading.Event()
        self.last_image = None
    
    def __getattr__(self, attr):
        """
        Accesses remote camera attributes as if they were local.

        Examples
        --------
        >>> print(ThorCamClient.color)
        False
        >>> print(ThorCamClient.brightness)
        5        
        """
        if attr == 'remote_attributes':
            return super().__getattr__(attr)
        elif attr in self.remote_attributes:
            return super().__getattr__(attr)
        else:
            return self.__dict__[attr]
    
    def __setattr__(self, attr, value):
        """
        Sets remote camera attributes as if they were local.

        Examples
        --------
        >>> ThorCamClient.color = True
        >>> ThorCamClient.brightness = 8
        >>> ThorCamClient.exposure = 100
        """
        if attr == 'remote_attributes':
            return super().__setattr__(attr,value)
        elif attr in self.remote_attributes:
            return setattr(self.cam, attr, value)
        else:
            return super().__setattr__(attr,value)

    def connect(self, name: str) -> None:
        """
        Connect to a remote PyroLab-hosted UC480 camera.

        Assumes the nameserver where the camera is registered is already 
        configured in the environment.

        Parameters
        ----------
        name : str
            The name used to register the camera on the nameserver.

        Examples
        --------
        >>> from pyrolab.api import NameServerConfiguration
        >>> from pyrolab.drivers.cameras.thorcam import ThorCamClient
        >>> nscfg = NameServerConfiguration(host="my.nameserver.com")
        >>> nscfg.update_pyro_config()
        >>> cam = ThorCamClient()
        >>> cam.connect("camera_name")
        """
        with locate_ns() as ns:
            self.cam = Proxy(ns.lookup(name))
        self.cam.autoconnect()
        self.remote_attributes = self.cam._pyroAttrs
        self._LOCAL_HEADERSIZE = self.HEADERSIZE
    
    def start_stream(self) -> None:
        """
        Starts the video stream.

        Sets up the remote camera to start streaming and opens a socket 
        connection to receive the stream. Starts a new daemon thread to 
        constantly receive images.
        """
        address, port = self.cam.start_capture()
        self.clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clientsocket.connect((address, port))

        self.stop_video.clear()
        self.video_thread = threading.Thread(target=self._receive_video_loop, args=())
        self.video_thread.daemon = True
        self.video_thread.start()

    def _decode_header(self, header):
        """
        Decodes the header of the image.

        Image header consists of four np.uintc values, ordered as [length of 
        message (in bytes), width, height, depth (usually 1, or 3 if color)].

        Parameters
        ----------
        header : bytes
            The header of the image.

        Returns
        -------
        length, shape : int, tuple(int, int, int)
            The length in bytes of the image, and its shape (for np.reshape).
        """
        length, *shape = np.frombuffer(header, dtype=np.uint32)
        return length, shape
    
    def _receive_video_loop(self) -> None:
        while not self.stop_video.is_set():
            message = b''
            
            # Read size of the incoming message
            header = self.clientsocket.recv(self._LOCAL_HEADERSIZE)
            length, shape = self._decode_header(header)
            while len(message) < length:
                submessage = self.clientsocket.recv(self.SUB_MESSAGE_LENGTH)
                message += submessage

            # Deserialize the message and break
            self.last_image = np.frombuffer(message, dtype=np.uint8).reshape(shape)
            self.clientsocket.send(b'ACK')

        self.clientsocket.close()
        self.cam.stop_capture()

    def end_stream(self) -> None:
        """
        Ends the video stream.
        
        Ends the video stream by setting the stop_video flag and closing the
        socket connection. Because communication is via a flag, shutdown
        may not be instantaneous.
        """
        self.stop_video.set()

    def await_stream(self, timeout: float = 3.0) -> bool:
        """
        Blocks until the first image is available from the stream.

        Parameters
        ----------
        timeout : float
            The number of seconds to wait for the first image (default 3).

        Returns
        -------
        bool
            ``True`` if an image is available, ``False`` otherwise.
        """
        start = time.time()
        while self.last_image is None:
            if time.time() - start > timeout:
                return False
            time.sleep(0.001)
        return True

    def get_frame(self) -> np.ndarray:
        """
        Returns the last image received from the stream.

        You should make sure to call :py:meth:`await_stream` before calling
        this method.

        Returns
        -------
        np.ndarray
            The last image received from the stream.

        Examples
        --------
        >>> cam = ThorCamClient()
        >>> cam.connect("camera_name")
        >>> cam.start_stream()
        >>> cam.await_stream()
        >>> frame = cam.get_frame()        
        """
        return self.last_image

    def close(self) -> None:
        """
        Closes the Proxy connection to the remote camera.
        """
        self.cam.close()
        self.remote_attributes = []
