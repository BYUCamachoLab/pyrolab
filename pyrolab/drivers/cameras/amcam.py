import pythoncom
from pyrolab.drivers.cameras import uvcsam, Camera
from pyrolab.api import expose


import numpy as np

from pyrolab.api import locate_ns, Proxy
import cv2 as cv


import socket
import threading
import time
from ctypes import *
from typing import Tuple, Optional

@expose
class DM756_U830(Camera):
    
    def __init__(self):
        pythoncom.CoInitialize()
        self._hcam = None
        self.frame = 0
        self.imgWidth = 0
        self.imgHeight = 0
        self.pData = None
        self.data_buffer = []
        self.data_buffer_size = 10
        self._cam_id = None
        self.stop_video = threading.Event()
        self.local = False
        self._logs = ""
        self._conn_count = 0
        self.frames_sent = 0
        self.IMAGE_WIDTH = 3840
        self.IMAGE_HEIGHT = 2160
        self.IMAGE_CHANNELS = 3
    
    
    def connect(self, cam_idx=0, local=False):
        self._logs = ""
        self.local = local
        arr = uvcsam.Uvcsam.enum()
        self.log(f'connecting to camera {self._conn_count}')
        self._conn_count += 1
        if len(arr) == 0:
            self.log("Warning, No camera found.")
        elif 1 == len(arr):
            self._cam_id = arr[0].id
        else:
            if cam_idx >= len(arr):
                self.log("Warning, Camera index out of range.")
            else:
                self._cam_id = arr[cam_idx].id
    
    def start_capture(self):
        self.log('starting capture')
        self.open_camera(self.cam_id)
        if not self.local:
            return self.start_streaming_thread()
    
    @property
    def cam_id(self):
        return self._cam_id
     
    @property
    def cam_connected(self):
        return self._hcam is not None
    
    @property
    def logs(self):
        return self._logs
    
    def log(self, msg):
        self._logs += msg + '\n'
    
    def open_camera(self, id):
        self.log('opening camera')
        self._hcam = uvcsam.Uvcsam.open(id)
        if self._hcam:
            self.frame = 0
            self._hcam.put(uvcsam.UVCSAM_FORMAT, 2) #Qimage use RGB byte order

            res = self._hcam.get(uvcsam.UVCSAM_RES)
            self.imgWidth = self._hcam.get(uvcsam.UVCSAM_WIDTH | res)
            self.imgHeight = self._hcam.get(uvcsam.UVCSAM_HEIGHT | res)
            self.buf_size = uvcsam.TDIBWIDTHBYTES(self.imgWidth * 24) * self.imgHeight
            self.pData = bytes(self.buf_size)
            try:
                self._hcam.start(None, self.event_call_back, self) # Pull Mode
            except uvcsam.HRESULTException as ex:
                self.closeCamera()
                self.log('failed to start camera, hr=0x{:x}'.format(ex.hr))

    @staticmethod
    def event_call_back(nEvent, self):
        self.event_handler(nEvent)

    def event_handler(self, nEvent):
        if self._hcam is not None:
            if uvcsam.UVCSAM_EVENT_ERROR & nEvent != 0:
                self.closeCamera()
                self.log('Error: Camera error.')
            elif uvcsam.UVCSAM_EVENT_DISCONNECT & nEvent != 0:
                self.closeCamera()
                self.log('Error: Camera disconnected.')
            else:
                if uvcsam.UVCSAM_EVENT_IMAGE & nEvent != 0:
                    self.onImageEvent()
                if uvcsam.UVCSAM_EVENT_EXPOTIME & nEvent != 0:
                    self.updateExpoTime()
                if uvcsam.UVCSAM_EVENT_GAIN & nEvent != 0:
                    self.updateGain()
    
    def onImageEvent(self):
        self._hcam.pull(self.pData) # Pull Mode    
        self.frame += 1
        self._buffer_data(self.pData)
    
    def closeCamera(self):
        if self._hcam:
            self._hcam.close()
        self._hcam = None
        self.pData = None
        
    def updateExpoTime(self):
        self.expo_time = self._hcam.get(uvcsam.UVCSAM_EXPOTIME)
        
    def updateGain(self):
        self.gain = self._hcam.get(uvcsam.UVCSAM_GAIN)
        
    def _buffer_data(self, data):
        
        if len(self.data_buffer) < self.data_buffer_size:
            self.data_buffer.append(data)
        else:
            self.data_buffer.pop(0)
            self.data_buffer.append(data)
            
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
        # log.debug(f"Received: {size} {d1} {d2} {d3}")
        return np.array((size, d1, d2, d3), dtype=np.uintc)  
    
    def _remote_streaming_loop(self):
        """
        Starts a separate thread to stream frames.

        This function is called as a separate thread when streaming is initiated.
        It will loop, sending frame by frame across the socket connection,
        until the ``stop_video`` is set (by :py:func:`stop_capture`).

        Sends a single image and waits for ACK before sending the next image.
        """
        self.log("Waiting for client to connect...")
        self.serversocket.listen(5)
        self.clientsocket, address = self.serversocket.accept()
        self.clientsocket.settimeout(5.0)
        self.log("Accepted client socket")

        while not self.stop_video.is_set():
            raw_frame = self.get_frame()
            if raw_frame is None:
                self.log("No frame received")
                continue
            encode_param = [int(cv.IMWRITE_JPEG_QUALITY), 90]
            success, msg = cv.imencode(".jpg", self.get_frame(), encode_param)
            if not success:
                self.log("Compression failed")
                continue
            # self.log("Serializing")
            ser_msg = msg.tobytes()
            header = self._write_header(len(ser_msg), *msg.shape)
            ser_msg = header.tobytes() + ser_msg
            try:
                ser_msg = self.pop_data()
                if ser_msg is None:
                    continue
                total_sent = 0
                while total_sent < len(ser_msg):
                    sent = self.clientsocket.send(ser_msg[total_sent:])
                    if sent == 0:
                        self.log("Socket connection broken")
                        raise RuntimeError("Socket connection broken")
                    total_sent += sent
                self.frames_sent += 1
            except TimeoutError:
                self.log('Connection timed out!')
                self.end_stream()
            except Exception as e:
                self.log(f"Error: {e}")
                self.end_stream()
        self.log(f"Video loop ended after sending {self.frames_sent} frames")
        

    def end_stream(self) -> None:
        """
        Ends the video stream.

        Ends the video stream by setting the stop_video flag and closing the
        socket connection. Because communication is via a flag, shutdown
        may not be instantaneous.
        """
        self.stop_video.set()
        self.log("set stop_video flag")
        self.clientsocket.close()
        self.log("Video stream ended")
    
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
        self.log(f"Socket bound to {self.serversocket.getsockname()}")
        return self.serversocket.getsockname()

    def start_streaming_thread(self) -> Tuple[str, int]:
        """
        Starts the streaming thread for nonlocal connections.

        Returns
        -------
        address, port : str, int
            The address and port of the socket providing the stream.
        """
        self.log("Setting up socket for streaming")
        self.stop_video.clear()
        address, port = self._get_socket()
        self.video_thread = threading.Thread(
            target=self._remote_streaming_loop, args=()
        )
        self.video_thread.start()
        return [address, port]
        
    def set_gain(self, gain):
        self._hcam.put(uvcsam.UVCSAM_GAIN, gain)
        self.gain = gain
        
    def get_gain(self):
        return self.gain
        
    def set_expo_time(self, expo_time):
        self._hcam.put(uvcsam.UVCSAM_EXPOTIME, expo_time)
        self.expo_time = expo_time
        
    def get_expo_time(self):
        return self.expo_time
        
    def get_auto_expo(self):
        return self._hcam.get(uvcsam.UVCSAM_AE_ONOFF)
    
    def set_auto_expo(self, auto_expo):
        self._hcam.put(uvcsam.UVCSAM_AE_ONOFF, auto_expo)
    
    def pop_data(self):
        if len(self.data_buffer) > 0:
            return self.data_buffer.pop(0)
        else:
            return None
        
    def get_frame(self):
        print('Getting frame')
        if len(self.data_buffer) > 0:
            data = self.pop_data()
            if data is not None:
                img = np.frombuffer(data, np.uint8)
                # print(img.shape)
                img = img.reshape(self.IMAGE_CHANNELS, self.IMAGE_WIDTH, self.IMAGE_HEIGHT, order='C')
                img.shape = (self.IMAGE_HEIGHT, self.IMAGE_WIDTH, self.IMAGE_CHANNELS)
                img = np.flip(img, [0,2])
            else:
                img = None
            return img
        else:
            return None
        
    def stop_capture(self):
        self.log('stopping capture')
        if not self.local:
            self.log('not local, ending stream')
            self.end_stream()
            self.closeCamera()
            
    def close(self):
        self.closeCamera()
    
    
class DM756_U830Client:
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

    def __init__(self, on_new_frame=None):
        self.remote_attributes = []
        self.SUB_MESSAGE_LENGTH = 4096*2160*8
        self.IMAGE_WIDTH = 3840
        self.IMAGE_HEIGHT = 2160
        self.IMAGE_CHANNELS = 3
        self.IMAGE_STRUCT = np.zeros([self.IMAGE_WIDTH, self.IMAGE_HEIGHT, self.IMAGE_CHANNELS], dtype=np.uint8)
        self.IMAGE_MESSAGE_SIZE = self.IMAGE_STRUCT.itemsize * self.IMAGE_STRUCT.size
        self.stop_video = threading.Event()
        self.video_stopped = threading.Event()
        self.last_image = None
        self._logs = ""
        self.cam_logs_bu = ""
        self.frames_received = 0
        self.new_image = False
        self.on_new_frame = on_new_frame

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

    def cam_connect(self, name: str = "device", ns=None, uri=None) -> None:
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
        self.log('connecting to camera')
        
        if uri is not None:
            self.cam = Proxy(uri)
        elif ns is not None:
            self.cam = Proxy(ns.lookup(name))
        
        self.cam.connect()
    
    def start_stream(self) -> None:
        """
        Starts the video stream.

        Sets up the remote camera to start streaming and opens a socket
        connection to receive the stream. Starts a new daemon thread to
        constantly receive images.
        """
        self.log("Starting video stream")
        address, port = self.cam.start_capture()
        self.clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clientsocket.settimeout(5.0)
        self.clientsocket.connect((address, port))
        self.log("Connected to socket")

        self.stop_video.clear()
        self.video_stopped.clear()
        self.video_thread = threading.Thread(target=self._receive_video_loop, args=())
        self.video_thread.daemon = True
        self.video_thread.start()
        self.log("Started video thread")

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
    
    def _serial_to_image(self, serial: bytes) -> np.ndarray:
        """
        Converts a serialized image to a numpy array.

        Parameters
        ----------
        serial : bytes
            The serialized image.

        Returns
        -------
        np.ndarray
            The deserialized image.
        """
        if len(serial) != self.IMAGE_MESSAGE_SIZE:
            self.log(f"Received message of size {len(serial)}, expected {self.IMAGE_MESSAGE_SIZE} bytes.")
            return None
        img = np.frombuffer(serial, np.uint8)
        # print(img.shape)
        img = img.reshape(self.IMAGE_CHANNELS, self.IMAGE_WIDTH, self.IMAGE_HEIGHT, order='C')
        img.shape = (self.IMAGE_HEIGHT, self.IMAGE_WIDTH, self.IMAGE_CHANNELS)
        img = np.flip(img, [0,2])
        return img

    def _receive_video_loop(self) -> None:
        self.log("Starting video loop")
        while not self.stop_video.is_set():
            message = b""
            header = b""

            # Read size of the incoming message
            try:
                while len(message) < self._LOCAL_HEADERSIZE:
                    sub_header = self.clientsocket.recv(min(self._LOCAL_HEADERSIZE, self._LOCAL_HEADERSIZE - len(message)))
                    header += sub_header
                length, shape = self._decode_header(header)
                
                while len(message) < length:
                    submessage = self.clientsocket.recv(min(self.SUB_MESSAGE_LENGTH, self.IMAGE_MESSAGE_SIZE - len(message)))
                    if submessage == b"":
                        self.log("Socket connection broken")
                        raise RuntimeError("Socket connection broken")
                    message += submessage
                self.frames_received += 1
            except TimeoutError:
                self.log('Connection timed out!')
                self.end_stream()
            except Exception as e:
                self.log(f"Error: {e}")
                self.end_stream()

            # self.last_image = self._serial_to_image(message)
            self.last_image = cv.imdecode(
                np.frombuffer(message, dtype=np.uint8).reshape(shape), 1
            )
            if self.on_new_frame is not None:
                self.on_new_frame(self.last_image)
            self.new_image = True
        self.log(f"Video loop ended after receiving {self.frames_received} frames")
        self.clientsocket.close()
        self.log("Client socket closed")
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
        self.cam_logs_bu = self.cam.logs
        self.log('stopping camera')
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
        self.log("Waiting for stream")
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
        is_new = self.new_image
        if is_new:
            self.new_image = False
        return self.last_image, is_new

    def close(self) -> None:
        """
        Closes the Proxy connection to the remote camera.
        """
        self.cam.close()
        self.remote_attributes = []
    
    @property
    def logs(self):
        return self._logs
    
    def log(self, msg):
        self._logs += msg + '\n'
    
    @property
    def cam_logs(self):
        return self.cam.logs
    
    @property
    def cam_connected(self):
        return self.cam.cam_connected
