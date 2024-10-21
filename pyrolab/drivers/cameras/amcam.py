import cv2
from pyrolab.api import expose, locate_ns, Proxy
from pyrolab.drivers.cameras import Camera
from pyrolab.drivers import Instrument

@expose
class AmScope(Camera):
    def __init__(self, cam_idx=0):
        self.cam_idx = cam_idx
        self.capture = None
    
    @expose
    def start_camera(self):
        self.capture = cv2.VideoCapture(self.cam_idx)
        if not self.capture.isOpened():
            raise Exception("Could not open video device")
        return self.capture
    
    @expose
    def stop_camera(self):
        if self.capture is not None:
            self.capture.release()
            self.capture = None
            
    @expose 
    def autoconnect(self):
        return super().autoconnect()
    
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
        self.cam.autoconnect()
        self.remote_attributes = self.cam._pyroAttrs
        self._LOCAL_HEADERSIZE = self.HEADERSIZE
        

