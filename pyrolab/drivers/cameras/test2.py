import uvcsam, pythoncom
import cv2 as cv
import numpy as np

class App:
    def __init__(self):
        self.hcam = None
        self.buf = None
        self.total = 0

    @staticmethod
    def cameraCallback(nEvent, ctx):
        ctx.CameraCallback(nEvent)

    def CameraCallback(self, nEvent):
        if nEvent & uvcsam.UVCSAM_EVENT_IMAGE != 0:
            self.hcam.pull(self.buf) # Pull Mode
            
            
            self.total += 1
            print('image ok, total = {}'.format(self.total))
            cv.namedWindow('frame', cv.WINDOW_NORMAL)
            img = np.frombuffer(self.buf, np.uint8)
            print(img.shape)
            img = img.reshape(3, 3840, 2160, order='C')
            img.shape = (2160, 3840, 3)
            cv.imshow('frame', img)
            cv.waitKey(1)
            # print(f'cv image shape: {img.shape}')
        else:
            print('event callback: {}'.format(nEvent))

    def run(self):
        a = uvcsam.Uvcsam.enum()
        if len(a) > 0:
            print('name = {} id = {}'.format(a[0].displayname, a[0].id))
            self.hcam = uvcsam.Uvcsam.open(a[0].id)
            if self.hcam:
                try:
                    res = self.hcam.get(uvcsam.UVCSAM_RES)
                    width = self.hcam.get(uvcsam.UVCSAM_WIDTH | res)
                    height = self.hcam.get(uvcsam.UVCSAM_HEIGHT | res)
                    bufsize = uvcsam.TDIBWIDTHBYTES(width * 24) * height
                    print('image size: {} x {}, bufsize = {}'.format(width, height, bufsize))
                    self.buf = bytes(bufsize)
                    if self.buf:
                        try:
                            self.hcam.start(None, self.cameraCallback, self) # Pull Mode
                        except uvcsam.HRESULTException as ex:
                            print('failed to start camera, hr=0x{:x}'.format(ex.hr))
                    input('press ENTER to exit')
                finally:
                    self.hcam.close()
                    self.hcam = None
                    self.buf = None
            else:
                print('failed to open camera')
        else:
            print('no camera found')

if __name__ == '__main__':
    pythoncom.CoInitialize()    # ATTENTION: initialize COM
    app = App()
    app.run()