# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Thorlabs Scientific Camera
==========================

Driver for a Thorlabs Scientific Camera.

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

import time
import logging
from ctypes import *

import numpy as np
from thorlabs_kinesis import thor_science_camera as tc
from pyrolab.drivers.cameras.thorcam import ThorCamBase

from pyrolab.api import expose

log = logging.getLogger(__name__)

@expose
class SCICAM(ThorCamBase):
    """
    Driver for the ThorLabs SCICAM.

    Attributes
    ----------
    HEADERSIZE : int
        The size of the header used to communicate the size of the message
        (10 bytes is a safe size).
    """
    
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
        min_exposure = c_longlong()
        max_exposure = c_longlong()
        error = tc.GetExposureTimeRange(self.handle,min_exposure,max_exposure)
        if(exposure < min_exposure.value):
            exposure = min_exposure.value
        if(exposure > max_exposure.value):
            exposure = max_exposure.value
        exp_c = c_longlong(exposure)
        error = tc.SetExposure(self.handle,exp_c)
        log.debug(f"exposure set with error {error}")

    def connect(self, 
                serialno: str,
                local: bool = False,
                bit_depth: int = 8,
                color: bool = True,
                exposure: int = 90, 
                brightness: int = 5
    ):
        """
        Opens the serial communication with the Thorlabs camera.
        
        Sets some low-level values, including the bit depth and camera name.

        Parameters
        ----------
        serialno : int
            The serial number of the camera that should be connected to.
        color : bool, optional
            Whether the camera is in color mode or not (default True).
        exposure: int, optional
            In milliseconds, the time the shutter is open on the camera 
            (default 10,000).
        brightness : int
            Integer (range 1-10) defining the brightness, where 5 leaves the 
            brightness unchanged.
        """
        self.local = local
        self.bit_depth = bit_depth
        ser_no_list = create_string_buffer(4096)
        length = c_int(4096)
        error = tc.OpenSDK()
        error = tc.DiscoverAvailableCameras(ser_no_list,length)
        log.debug(f"serial number list: {str(ser_no_list.value.decode()).strip()}")
        if(str(serialno) == str(ser_no_list.value.decode()).strip()):
            self.handle = c_void_p()
            log.debug("camera found")
            error = tc.OpenCamera(ser_no_list.value, self.handle)
            log.debug(f"camera opened with error {error}")

        log.debug("setting exposure...")
        self.exposure = exposure
        self.find_sensor_size()
    
    def find_sensor_size(self):
        height = c_int()
        error = tc.GetImageHeight(self.handle,height)
        width = c_int()
        error = tc.GetImageWidth(self.handle,width)
        self.height = int(height.value)
        self.width = int(width.value)
        self.roi_shape = [int(self.width/2),int(self.height/2)]
        self.roi_pos = [0,0]
        log.debug(f"sensor size found {self.width} x {self.height}")

    def get_frame(self):
        """
        Retrieves the last frame from the memory buffer, processes
        it into a gray-scale image, and serializes it using the pickle
        library. The header is then added to inform the client how long
        the message is. This should not be called from the client. It
        will be called from the function _video_loop() which is on a
        parallel thread with Pyro5.
        """
        image_buffer = POINTER(c_ushort)()
        frame_count = c_int(0)
        metadata_pointer = POINTER(c_char)()
        metadata_size_in_bytes = c_int()
        log.debug("getting frame...")
        while frame_count.value == 0:
            tc.GetFrameOrNull(self.handle, image_buffer, frame_count, metadata_pointer, metadata_size_in_bytes)
        image_buffer._wrapper = self
        raw = np.ctypeslib.as_array(image_buffer,shape=(self.height,self.width))
        bayer =  self._bayer_convert(raw)
        return self._obtain_roi(bayer)
        

    @expose
    def start_capture(self):
        """
        Starts capture from the camera.

        This starts the capture from the camera to the allocated
        memory location as well as starts a new parallel thread
        for the socket server to stream from memory to the client.

        Returns
        -------
        ip_address : str
            The delivery IP address of the video stream.
        """
        error = tc.ArmCamera(self.handle,c_int(2))
        error = tc.IssueSoftwareTrigger(self.handle)
        if not self.local:
            time.sleep(1)
            return self.start_streaming_thread()

    @expose
    def stop_capture(self):
        """
        Stops the capture from the camera.

        This frees the memory used for storing the frames then triggers
        the stop_video event which will end the parrallel socket thread.
        """

        if self.local == False:
            self.stop_streaming_thread()
        error = tc.DisarmCamera(self.handle)
        log.debug(f"error: {error}")

    @expose
    def close(self):
        """
        Closes communication with the camera and frees memory.

        Calls :py:func:`stop_capture` to free memory and end the socket server
        and then s serial communication with the camera.

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
        error = tc.CloseCamera(self.handle)
        log.debug(f"error: {error}")
        error = tc.CloseSDK()
        log.debug(f"error: {error}")
        # del self.handle
