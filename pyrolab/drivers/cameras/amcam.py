import sys
import uvcsam
class DMSomething():
    
    def __init__(self):
        self.hcam = None
        self.frame = 0
        self.imgWidth = 0
        self.imgHeight = 0
        self.pData = None
        self.data_buffer = []
        self.data_buffer_size = 10
    
    def connect(self, cam_idx=0):
        arr = uvcsam.Uvcsam.enum()
        if len(arr) == 0:
            print("Warning", "No camera found.")
        elif 1 == len(arr):
            self.openCamera(arr[0].id)
        else:
            if cam_idx >= len(arr):
                print("Warning", "Camera index out of range.")
            else:
                self.openCamera(arr[cam_idx].id)
    
    def openCamera(self, id):
        self.hcam = uvcsam.Uvcsam.open(id)
        if self.hcam:
            self.frame = 0
            self.hcam.put(uvcsam.UVCSAM_FORMAT, 2) #Qimage use RGB byte order

            res = self.hcam.get(uvcsam.UVCSAM_RES)
            self.imgWidth = self.hcam.get(uvcsam.UVCSAM_WIDTH | res)
            self.imgHeight = self.hcam.get(uvcsam.UVCSAM_HEIGHT | res)
            self.buf_size = uvcsam.TDIBWIDTHBYTES(self.imgWidth * 24) * self.imgHeight
            self.pData = bytes(self.buf_size)
            try:
                self.hcam.start(None, self.eventCallBack, self) # Pull Mode
            except uvcsam.HRESULTException as ex:
                self.closeCamera()
                print('failed to start camera, hr=0x{:x}'.format(ex.hr))

    def eventCallBack(nEvent, self):
        self.event_handler(nEvent)

    def event_handler(self, nEvent):
        if self.hcam is not None:
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
        self.hcam.pull(self.pData) # Pull Mode    
        self.frame += 1
        self._buffer_data(self.pData)
    
    def closeCamera(self):
        if self.hcam:
            self.hcam.close()
        self.hcam = None
        self.pData = None
        
    def updateExpoTime(self):
        self.expo_time = self.hcam.get(uvcsam.UVCSAM_EXPOTIME)
        
    def updateGain(self):
        self.gain = self.hcam.get(uvcsam.UVCSAM_GAIN)
        
    def _buffer_data(self, data):
        
        if len(self.data_buffer) < self.data_buffer_size:
            self.data_buffer.append(data)
        else:
            self.data_buffer.pop(0)
            self.data_buffer.append(data)
        
    def set_gain(self, gain):
        self.hcam.put(uvcsam.UVCSAM_GAIN, gain)
        self.gain = gain
        
    def set_expo_time(self, expo_time):
        self.hcam.put(uvcsam.UVCSAM_EXPOTIME, expo_time)
        self.expo_time = expo_time
        
    def get_auto_expo(self):
        return self.hcam.get(uvcsam.UVCSAM_AE_ONOFF)
    
    def set_auto_expo(self, auto_expo):
        self.hcam.put(uvcsam.UVCSAM_AE_ONOFF, auto_expo)
    
    def get_frame(self):
        if len(self.data_buffer) > 0:
            return self.data_buffer[0]
        else:
            return None
    
    def close(self):
        self.closeCamera()
    
    
class DMSomethingClient:
    def __init__(self, url):
        self.url = url
        # self.conn = xmlrpclib.ServerProxy(url)
        
    def connect(self):
        return self.conn.connect()
    
    def get_frame(self):
        return self.conn.get_frame()
    
    def disconnect(self):
        return self.conn.disconnect