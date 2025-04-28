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

   thorlabs_kinesis (installed with pyrolab[thorlabs], see :ref:`configuration instructions <Thorlabs Kinesis Package>`)
"""

# TODO: Investigate Linux support
# (https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=ThorCam)

import logging
from ctypes import *
from typing import Tuple

import numpy as np

try:
    from thorlabs_kinesis import thor_camera as tc
except:
    pass

from pyrolab.api import expose
from pyrolab.drivers.cameras.thorcam import ThorCamBase, ThorCamClient


log = logging.getLogger(__name__)


@expose
class UC480(ThorCamBase):
    """
    The Thorlabs UC480 camera driver.

    Attributes
    ----------
    HEADERSIZE : int
    brightness : int
    color : bool
    roi_shape : (int, int)
    roi_pos : (int, int)
    pixelclock : int
    exposure : int
    framerate : int
    """

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
            raise ConnectionError("Cannot set pixelclock before connecting to device.")

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
            tc.SetExposure(self.handle, 12, exposure_c, sizeof(exposure_c))
        else:
            raise ConnectionError("Cannot set exposure before connecting to device.")

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
            raise ConnectionError("Cannot set framerate before connecting to device.")

    def connect(
        self,
        serialno: str,
        local: bool = False,
        bit_depth: int = 8,
        pixelclock: int = 24,
        color: bool = True,
        colormode: int = 11,
        roi_shape: Tuple[int, int] = (1024, 1280),
        roi_pos: Tuple[int, int] = (0, 0),
        framerate: int = 15,
        exposure: int = 90,
        pixelbytes: int = 8,
        brightness: int = 5,
    ):
        """
        Opens the serial communication with the Thorlabs camera and sets defaults.

        Default low-level values that are set include the bit depth and camera
        name.

        Parameters
        ----------
        serialno : int
            The serial number of the camera that should be connected.
        local : bool, optional
            Whether the camera is being used as a local device; if True, will
            not configure sockets for streaming when starting capature (default
            False).
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
            if error != 0:
                continue

            info = tc.CAMINFO()
            error = tc.GetCameraInfo(handle, byref(info))

            if int(info.SerNo) == serialno:
                self.handle = handle
                break
            elif i == num.value - 1:
                raise ConnectionError("Camera not found")
            else:
                error = tc.ExitCamera(handle)
                if error != 0:
                    log.error(f"Closing ThorCam failed with error code {error}")

        self.bit_depth = bit_depth

        tc.SetDisplayMode(self.handle, c_int(32768))

        self.meminfo = None

        self.pixelclock = pixelclock
        self.framerate = framerate
        self.exposure = exposure
        self.brightness = brightness
        self.set_color_mode(colormode)
        self._set_hardware_roi_shape(roi_shape)
        self.roi_shape = [int(roi_shape[1] / 2), int(roi_shape[0] / 2)]
        self._set_hardware_roi_pos(roi_pos)
        self.roi_pos = [int(roi_pos[1] / 2), int(roi_pos[0] / 2)]
        self._initialize_memory(pixelbytes)

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
        raw = np.frombuffer(self.meminfo[0], c_ubyte).reshape(
            self.hardware_roi_shape[1], self.hardware_roi_shape[0]
        )
        log.debug(f"Retreived (size {raw.shape})")

        bayer = self._bayer_convert(raw)
        return self._obtain_roi(bayer)

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
            return self.start_streaming_thread()

    @expose
    def stop_capture(self) -> None:
        """
        Stops the capture from the camera.

        This frees the memory used for storing the frames, then (for remote
        connections) sets the stop_video flag which will close the daemon
        socket thread (not necessarily immediately).
        """
        tc.FreeMemory(self.handle, self.meminfo[0], self.meminfo[1])
        tc.StopCapture(self.handle, 1)
        if not self.local:
            self.stop_streaming_thread()

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
        tc.AllocateMemory(
            self.handle, xdim, ydim, c_int(pixelbytes), c_buf, byref(memid)
        )
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
        tc.AOI(self.handle, 3, byref(AOI_pos), 8)

        # 6 for getting size, 4 for getting position
        tc.AOI(self.handle, 4, byref(AOI_pos), 8)

        self.hardware_roi_pos = [AOI_pos.s32X, AOI_pos.s32Y]

    @expose
    def close(self):
        """
        Closes communication with the camera and frees memory.

        Calls :py:func:`stop_capture` to free memory and end the socket server
        and then closes serial communication with the camera.
        """
        try:
            self.handle
        except AttributeError:
            return

        self.stop_capture()

        error = tc.ExitCamera(self.handle)
        if error != 0:
            log.error(f"Closing ThorCam failed (code {error})")
        del self.handle
        self.meminfo = None


class UC480Client(ThorCamClient):
    pass
