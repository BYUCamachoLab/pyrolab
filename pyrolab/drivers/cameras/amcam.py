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
        self.cam_id = None
        self.stop_video = threading.Event()
        self.local = False
        self._logs = ""
    
    
    def connect(self, cam_idx=0, local=False):
        self.local = local
        arr = uvcsam.Uvcsam.enum()
        self.log('connecting to camera')
        if len(arr) == 0:
            self.log("Warning", "No camera found.")
        elif 1 == len(arr):
            self.cam_id = arr[0].id
        else:
            if cam_idx >= len(arr):
                self.log("Warning", "Camera index out of range.")
            else:
                self.cam_id = arr[cam_idx].id
    
    def start_capture(self):
        self.log('starting capture')
        self.openCamera(self.cam_id)
        if not self.local:
            return self.start_streaming_thread()
                
    @property
    def cam_connected(self):
        return self._hcam is not None
    
    @property
    def logs(self):
        return self._logs
    
    def log(self, msg):
        self._logs += msg + '\n'
    
    def openCamera(self, id):
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
                self._hcam.start(None, self.eventCallBack, self) # Pull Mode
            except uvcsam.HRESULTException as ex:
                self.closeCamera()
                self.log('failed to start camera, hr=0x{:x}'.format(ex.hr))

    @staticmethod
    def eventCallBack(nEvent, self):
        self.event_handler(nEvent)

    def event_handler(self, nEvent):
        if self._hcam is not None:
            if uvcsam.UVCSAM_EVENT_ERROR & nEvent != 0:
                self.closeCamera()
                print(self, "Warning", "Generic error.")
            elif uvcsam.UVCSAM_EVENT_DISCONNECT & nEvent != 0:
                self.closeCamera()
                print(self, "Warning", "Camera disconnect.")
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
            # log.debug("Getting frame")
            # encode_param = [int(cv.IMWRITE_JPEG_QUALITY), 90]
            # success, msg = cv.imencode(".jpg", self.get_frame(), encode_param)

            # if not success:
            #     log.debug("Compression failed")

            # log.debug("Serializing")
            # ser_msg = msg.tobytes()
            # header = self._write_header(len(ser_msg), *msg.shape)
            # ser_msg = header.tobytes() + ser_msg

            try:
                ser_msg = self.pop_data()
                total_sent = 0
                self.log(f"Sending message ({len(ser_msg)} bytes)")
                while total_sent < len(self.ser_msg):
                    sent = self.clientsocket.send(ser_msg[total_sent:])
                    if sent == 0:
                        raise RuntimeError("Socket connection broken")
                    total_sent += sent
                self.log("Message sent")

                check_msg = self.clientsocket.recv(4096)
                self.log(f"ACK: {check_msg}")
            except TimeoutError:
                self.log('Connection timed out!')
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
            data = self.data_buffer.pop(0)
            if data is not None:
                img = np.frombuffer(data, np.uint8)
                img = img.reshape(3, 3840, 2160, order='C')
                img.shape = (2160, 3840, 3)
                img = np.flip(img, [0,2])
            else:
                img = None
                print('No data in buffer')
            return img
        else:
            return None
        
    def stop_capture(self):
        if not self.local:
            self.clientsocket.close()
            self.stop_video.set()
        
        
    
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

    def __init__(self):
        self.remote_attributes = []
        self.SUB_MESSAGE_LENGTH = 4096
        self.IMAGE_WIDTH = 3840
        self.IMAGE_HEIGHT = 2160
        self.IMAGE_CHANNELS = 3
        self.IMAGE_STRUCT = np.zeros([self.IMAGE_WIDTH, self.IMAGE_HEIGHT, self.IMAGE_CHANNELS], dtype=np.uint8)
        self.IMAGE_MESSAGE_SIZE = self.IMAGE_STRUCT.itemsize * self.IMAGE_STRUCT.size
        self.stop_video = threading.Event()
        self.video_stopped = threading.Event()
        self.last_image = None
        self._logs = ""

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
        self.log('connecting to camera')
        if ns_host or ns_port:
            args = {"host": ns_host, "port": ns_port}
        else:
            args = {}

        with locate_ns(**args) as ns:
            self.cam = Proxy(ns.lookup(name))
        self.cam.autoconnect()
    
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
        self.clientsocket.settimeout(15.0)
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
            return
        img = np.frombuffer(serial, np.uint8)
        # print(img.shape)
        img = img.reshape(self.IMAGE_CHANNELS, self.IMAGE_WIDTH, self.IMAGE_HEIGHT, order='C')
        img.shape = (self.IMAGE_HEIGHT, self.IMAGE_WIDTH, self.IMAGE_CHANNELS)
        img = np.flip(img, [0,2])
        return 

    def _receive_video_loop(self) -> None:
        while not self.stop_video.is_set():
            message = b""

            # Read size of the incoming message
            try:
                # header = self.clientsocket.recv(self._LOCAL_HEADERSIZE)
                # length, shape = self._decode_header(header)
                while len(message) < self.IMAGE_MESSAGE_SIZE:
                    submessage = self.clientsocket.recv(min(self.SUB_MESSAGE_LENGTH, self.IMAGE_MESSAGE_SIZE - len(message)))
                    if submessage == b"":
                        raise RuntimeError("Socket connection broken")
                    message += submessage
                self.log(f"Reced message of size {len(message)} bytes")
                
            except TimeoutError:
                self.log('Connection timed out!')
                self.end_stream()

            # Deserialize the message and break
            # self.last_image = cv.imdecode(
            #     np.frombuffer(message, dtype=np.uint8).reshape(shape), 1
            # )
            self.last_image = self._serial_to_image(message)
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
        return self.last_image

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
