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
import socket
import threading
import time
from ctypes import *
from typing import Tuple, Optional

import numpy as np
import cv2 as cv

from pyrolab.api import expose
from pyrolab.drivers.cameras import Camera
from pyrolab.api import locate_ns, Proxy


log = logging.getLogger(__name__)


class ThorCamBase(Camera):
    """
    The Thorlabs camera base driver.

    Attributes
    ----------
    HEADERSIZE : int
    brightness : int
    color : bool
    roi_shape : (int, int)
    roi_pos : (int, int)
    """

    def __init__(self):
        self._HEADERSTRUCT = np.zeros(4, dtype=np.uintc)
        self.stop_video = threading.Event()

        self.brightness = 5
        self.color = True

    @property
    @expose
    def HEADERSIZE(self) -> int:
        """The size in bytes of the header in each serialized message (read only)."""
        return self._HEADERSTRUCT.itemsize * self._HEADERSTRUCT.size

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
    def roi_shape(self) -> Tuple[int, int]:
        """The region of interest shape."""
        return self._software_roi_shape

    @roi_shape.setter
    @expose
    def roi_shape(self, shape: Tuple[int, int]) -> None:
        self._software_roi_shape = shape

    @property
    @expose
    def roi_pos(self) -> Tuple[int, int]:
        """Sets the upper left corner of the region of interest in pixels."""
        return self._software_roi_pos

    @roi_pos.setter
    @expose
    def roi_pos(self, pos: Tuple[int, int]) -> None:
        self._software_roi_pos = pos

    @expose
    def connect(self, *args, **kwargs):
        """
        Opens the serial communication with the Thorlabs camera and sets defaults.

        Not implemented in the base class. Should be overwritten by inheriting
        classes.
        """
        raise NotImplementedError

    def _obtain_roi(self, image: np.array) -> np.array:
        log.debug(f"shape of image: {image.shape}")
        log.debug(f"shape: {self.roi_shape}")
        log.debug(f"positions: {self.roi_pos}")
        if self.color:
            image = image[
                self.roi_pos[1] : self.roi_pos[1] + self.roi_shape[1],
                self.roi_pos[0] : self.roi_pos[0] + self.roi_shape[0],
                :,
            ]
        else:
            image = image[
                self.roi_pos[1] : self.roi_pos[1] + self.roi_shape[1],
                self.roi_pos[0] : self.roi_pos[0] + self.roi_shape[0],
            ]
        log.debug(f"new shape of image: {image.shape}")
        return image

    def _bayer_convert(self, raw: np.array) -> np.array:
        """
        Coverts the raw data to something that can be displayed on-screen.

        Image data is retrieved as a single-dimensional array. This function
        converts it into either multidimensional BGR or grayscale image.

        Parameters
        ----------
        raw : np.array
            The raw data that is received from the camera.

        Returns
        -------
        np.array
            The converted data.
        """
        ow = (raw.shape[0] // 4) * 4
        oh = (raw.shape[1] // 4) * 4

        R = raw[0::2, 0::2]
        B = raw[1::2, 1::2]
        G0 = raw[0::2, 1::2]
        G1 = raw[1::2, 0::2]

        if self.color:
            log.debug("Bayer convert (color)")
            frame_height = raw.shape[0] // 2
            frame_width = raw.shape[1] // 2

            G = G0[:oh, :ow] // 2 + G1[:oh, :ow] // 2

            bayer_R = np.array(R, dtype=np.uint8).reshape(frame_height, frame_width)
            bayer_G = np.array(G, dtype=np.uint8).reshape(frame_height, frame_width)
            bayer_B = np.array(B, dtype=np.uint8).reshape(frame_height, frame_width)

            log.debug("Stacking color data")
            dStack = np.clip(
                np.dstack(
                    (
                        bayer_B * (self.brightness / 5),
                        bayer_G * (self.brightness / 5),
                        bayer_R * (self.brightness / 5),
                    )
                ),
                0,
                np.power(2, self.bit_depth) - 1,
            ).astype("uint8")
        else:
            log.debug("Bayer convert (grayscale)")
            bayer = (
                R[:oh, :ow] // 3
                + B[:oh, :ow] // 3
                + (G0[:oh, :ow] // 2 + G1[:oh, :ow] // 2) // 3
            )
            frame_height = bayer.shape[0]
            frame_width = bayer.shape[1]

            bayer_T = np.array(bayer, dtype=np.uint8).reshape(frame_height, frame_width)

            log.debug("Stacking grayscale data")
            dStack = np.clip(
                bayer_T * (self.brightness / 5),
                0,
                np.power(2, self.bit_depth) - 1,
            ).astype("uint8")
        log.debug("Bayer data stacked")
        return dStack

    def get_frame(self) -> np.array:
        """
        Retrieves the last frame from the camera's memory buffer.

        .. warning::

           Not a Pyro exposed function, cannot be called from a Proxy. We
           recommend using the :py:class:`ThorCamClient` for streaming
           video/getting remote images.

        Retrieves the last frame from the camera memory buffer and processes it
        into a computer-readable image format.

        Can only be called after :py:func:`start_capture`.

        Returns
        -------
        img : np.array
            The last frame from the camera's memory buffer.
        """
        raise NotImplementedError

    def _write_header(
        self, size: int, d1: int = 1, d2: int = 1, d3: int = 1
    ) -> np.array:
        """
        Creates the message header for the image being transferred over socket.

        Format is an array of 4 ``np.uintc`` values, ordered as
        (size, d1, d2, d3) where d1, d2, d3 are the dimensions of the image
        (typically ``img.shape``, if ``img`` is a numpy array).

        Parameters
        ----------
        size : int
            The total length of the message (excluding the header).
        d1 : int, optional
            The shape of the first dimension of the image (default 1).
        d2 : int, optional
            The shape of the second dimension of the image (default 1).
        d3 : int, optional
            The shape of the third dimension of the image (default 1).
        """
        log.debug(f"Received: {size} {d1} {d2} {d3}")
        return np.array((size, d1, d2, d3), dtype=np.uintc)

    def _remote_streaming_loop(self):
        """
        Starts a separate thread to stream frames.

        This function is called as a separate thread when streaming is initiated.
        It will loop, sending frame by frame across the socket connection,
        until the ``stop_video`` is set (by :py:func:`stop_capture`).

        Sends a single image and waits for ACK before sending the next image.
        """
        log.debug("Waiting for client to connect...")
        self.serversocket.listen(5)
        self.clientsocket, address = self.serversocket.accept()
        self.clientsocket.settimeout(5.0)
        log.debug("Accepted client socket")

        while not self.stop_video.is_set():
            log.debug("Getting frame")
            encode_param = [int(cv.IMWRITE_JPEG_QUALITY), 90]
            success, msg = cv.imencode(".jpg", self.get_frame(), encode_param)

            if not success:
                log.debug("Compression failed")

            log.debug("Serializing")
            ser_msg = msg.tobytes()
            header = self._write_header(len(ser_msg), *msg.shape)
            ser_msg = header.tobytes() + ser_msg

            try:
                log.debug(f"Sending message ({len(ser_msg)} bytes)")
                self.clientsocket.send(ser_msg)
                log.debug("Message sent")

                check_msg = self.clientsocket.recv(4096)
                log.debug(f"ACK: {check_msg}")
            except TimeoutError:
                print('Connection timed out!')
                self.end_stream()

    def _get_socket(self) -> Tuple[str, int]:
        """
        Opens an socket on the local machine using an available port and binds to it.

        Returns
        -------
        address, port : Tuple[str, int]
            The address and port of the new socket.
        """
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversocket.settimeout(5.0)
        self.serversocket.bind((socket.gethostname(), 0))
        return self.serversocket.getsockname()

    def start_streaming_thread(self) -> Tuple[str, int]:
        """
        Starts the streaming thread for nonlocal connections.

        Returns
        -------
        address, port : str, int
            The address and port of the socket providing the stream.
        """
        log.debug("Setting up socket for streaming")
        self.stop_video.clear()
        address, port = self._get_socket()
        self.video_thread = threading.Thread(
            target=self._remote_streaming_loop, args=()
        )
        self.video_thread.start()
        return [address, port]

    @expose
    def start_capture(self) -> Optional[Tuple[str, int]]:
        """
        Signals the hardware to start capturing and sets up the streaming thread.

        Not implemented in the base class. Should be overwritten by inheriting
        classes.

        Returns
        -------
        address, port : str, int
            Address and port of the opened socket, if used remotely.
        """
        raise NotImplementedError

    def stop_streaming_thread(self):
        """
        Closes the socket connection and signals the streaming thread to shutdown.
        """
        self.clientsocket.close()
        self.stop_video.set()

    @expose
    def stop_capture(self) -> None:
        """
        Stops the capture from the camera.

        This frees the memory used for storing the frames then triggers
        the stop_video event which will end the parallel socket thread.
        """
        raise NotImplementedError

    @expose
    def close(self):
        """
        Closes communication with the camera and frees memory.

        This is not implemented in the base class, inheriting classes should
        implement this function. They should close the socket server
        and then closes serial communication with the camera.
        """
        raise NotImplementedError
    
    @expose
    def start_stream(self) -> None:
        '''
        Starts a camera stream.
        '''
        raise NotImplementedError
    
    @expose
    def end_stream(self) -> None:
        '''
        Ends a camera stream.
        '''
        raise NotImplementedError

    @expose
    def await_stream(self, timeout: float = 3.0) -> bool:
        raise NotImplementedError


class ThorCamClient:
    """
    The Thorlabs camera client. Not a PyroLab :py:class:`Service` object.

    Used for receiving video streamed over a socket connection from a
    :py:class:`ThorCamBase`-derived service.

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
        self.video_stopped = threading.Event()
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
        if attr in self.remote_attributes:
            return getattr(self.cam, attr)
        else:
            return super().__getattr__(attr)

    def __setattr__(self, attr, value):
        """
        Sets remote camera attributes as if they were local.

        Examples
        --------
        >>> ThorCamClient.color = True
        >>> ThorCamClient.brightness = 8
        >>> ThorCamClient.exposure = 100
        """
        if attr == "remote_attributes":
            return super().__setattr__(attr, value)
        elif attr in self.remote_attributes:
            return setattr(self.cam, attr, value)
        else:
            return super().__setattr__(attr, value)

    def connect(self, name: str, ns_host: str = None, ns_port: float = None) -> None:
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
        if ns_host or ns_port:
            args = {"host": ns_host, "port": ns_port}
        else:
            args = {}

        with locate_ns(**args) as ns:
            self.cam = Proxy(ns.lookup(name))
        self.cam.autconnect()
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
        self.clientsocket.settimeout(15.0)
        self.clientsocket.connect((address, port))

        self.stop_video.clear()
        self.video_stopped.clear()
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
        length, *shape = np.frombuffer(header, dtype=np.uintc)
        return length, shape

    def _receive_video_loop(self) -> None:
        while not self.stop_video.is_set():
            message = b""

            # Read size of the incoming message
            try:
                header = self.clientsocket.recv(self._LOCAL_HEADERSIZE)
                length, shape = self._decode_header(header)
                while len(message) < length:
                    submessage = self.clientsocket.recv(self.SUB_MESSAGE_LENGTH)
                    message += submessage
            except TimeoutError:
                print('Connection timed out!')
                self.end_stream()

            # Deserialize the message and break
            self.last_image = cv.imdecode(
                np.frombuffer(message, dtype=np.uint8).reshape(shape), 1
            )
            self.clientsocket.send(b"ACK")

        self.clientsocket.close()
        self.video_stopped.set()

    def end_stream(self) -> None:
        """
        Ends the video stream.

        Ends the video stream by setting the stop_video flag and closing the
        socket connection. Because communication is via a flag, shutdown
        may not be instantaneous.
        """
        self.stop_video.set()
        while not self.video_stopped.is_set():
            time.sleep(0.001)
        self.cam.stop_capture()

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
