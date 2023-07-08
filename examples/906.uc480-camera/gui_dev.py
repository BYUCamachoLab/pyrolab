# import the necessary packages
from __future__ import print_function
from PIL import Image
from PIL import ImageTk
import tkinter as tki
import threading
import datetime
import imutils
import cv2
import os
from pyrolab.api import locate_ns, Proxy
import numpy as np
import socket
import pickle
import time
from datetime import datetime

HEADERSIZE = 10
BRIGHTNESS = 5
PORT = 2222
SER_NUMBER = 4103257229
COLOR = True


class PhotoBoothApp:
    def __init__(self):
        # store the video stream object and output path, then initialize
        # the most recently read frame, thread for reading frames, and
        # the thread stop event
        self.outputPath = "C:/Users/hilld/Desktop"
        self.frame = None
        self.thread = None
        self.stopEvent = None

        # initialize the root window and image panel
        self.root = tki.Tk()
        self.panel = None

        # create a button, that when pressed, will take the current
        # frame and save it to file
        btn = tki.Button(self.root, text="Snapshot!", command=self.takeSnapshot)
        btn.pack(side="bottom", fill="both", expand="yes", padx=10, pady=10)

        # start a thread that constantly pools the video sensor for
        # the most recently read frame
        self.init_camera()
        self.stopEvent = threading.Event()
        self.thread = threading.Thread(target=self.videoLoop, args=())
        self.thread.start()

        # set a callback to handle when the window is closed
        self.root.wm_title("PyImageSearch PhotoBooth")
        self.root.wm_protocol("WM_DELETE_WINDOW", self.onClose)

    def clear(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def bayer_convert(self, bayer):
        if COLOR:
            ow = (bayer.shape[0] // 4) * 4
            oh = (bayer.shape[1] // 4) * 4

            R = bayer[0::2, 0::2]
            B = bayer[1::2, 1::2]
            G0 = bayer[0::2, 1::2]
            G1 = bayer[1::2, 0::2]
            G = G0[:oh, :ow] // 2 + G1[:oh, :ow] // 2
            bayer_R = np.array(R, dtype=np.uint8).reshape(512, 640)
            bayer_G = np.array(G, dtype=np.uint8).reshape(512, 640)
            bayer_B = np.array(B, dtype=np.uint8).reshape(512, 640)

            dStack = np.clip(
                np.dstack(
                    (
                        bayer_B * (BRIGHTNESS / 5),
                        bayer_G * (BRIGHTNESS / 5),
                        bayer_R * (BRIGHTNESS / 5),
                    )
                ),
                0,
                255,
            ).astype("uint8")
        else:
            bayer_T = np.array(bayer, dtype=np.uint8).reshape(512, 640)
            dStack = np.clip(
                (
                    np.dstack(
                        (
                            (0.469 + bayer_T * 0.75 - (bayer_T ^ 2) * 0.003)
                            * (BRIGHTNESS / 5),
                            (bayer_T * 0.95) * (BRIGHTNESS / 5),
                            (0.389 + bayer_T * 1.34 - (bayer_T ^ 2) * 0.004)
                            * (BRIGHTNESS / 5),
                        )
                    )
                ),
                0,
                255,
            ).astype("uint8")
        # dStack = np.clip(np.dstack((bayer,bayer,bayer)),0,255).astype('uint8')
        return dStack

    def init_camera(self):
        ns = locate_ns(host="camacholab.ee.byu.edu")
        objs = str(ns.list())
        while True:
            temp_str = objs[objs.find("'") + 1 : -1]
            temp_obj = temp_str[0 : temp_str.find("'")]
            if temp_obj[0:5] == "UC480":
                temp_ser_no = int(temp_obj[6 : len(temp_obj)])
                if temp_ser_no == SER_NUMBER:
                    cam_str = temp_obj
            if objs.find(",") == -1:
                break
            objs = objs[objs.find(",") + 1 : -1]
        try:
            cam_str
        except NameError:
            raise Exception(
                "Camera with serial number " + str(SER_NUMBER) + " could not be found"
            )

        self.cam = Proxy(ns.lookup(cam_str))

        self.cam.start(exposure=65)
        ip_address = self.cam.start_capture(COLOR)
        print("IP: " + str(ip_address))
        self.clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clientsocket.connect((str(ip_address), PORT))

        now = datetime.now()
        dt_string = now.strftime("rec_" + str(SER_NUMBER) + "/%Y-%m-%d_%H-%M-%S.avi")
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        self.out = cv2.VideoWriter(dt_string, fourcc, 4.0, (640, 512))

        self.time_s = 0
        self.frame_rate = 0
        self.count = -1
        self.vid = cv2.VideoCapture("test.mp4")

    def videoLoop(self):
        root = tki.Tk()
        while True:
            self.clear()
            if self.count >= 0:
                t = time.time() - self.time_s
                self.frame_rate = (self.frame_rate * self.count + 1 / t) / (
                    self.count + 1
                )

            self.time_s = time.time()
            self.count = self.count + 1

            msg = b""
            new_msg = True
            msg_len = None
            imList = None
            while True:
                if new_msg:
                    sub_msg = self.clientsocket.recv(HEADERSIZE)
                    msg_len = int((sub_msg[:HEADERSIZE]))
                    new_msg = False
                else:
                    sub_msg = self.clientsocket.recv(32800)
                    msg += sub_msg
                    if len(msg) == msg_len:
                        imList = pickle.loads(msg)
                        break

            dStack = self.bayer_convert(imList)

            # frame = Image.fromarray(dStack)
            self.out.write(dStack)

            ret, frame = self.vid.read()
            print(ret)

            img_1 = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image_mid = Image.fromarray(img_1)
            image = ImageTk.PhotoImage(image=image_mid)
            image.image = image_mid

            # if the panel is not None, we need to initialize it
            if self.panel is None:
                self.panel = tki.Label(image=image)
                self.panel.image = image
                self.panel.pack(side="left", padx=10, pady=10)

            # otherwise, simply update the panel
            else:
                self.panel.configure(image=image)
                self.panel.image = image

            cv2.imshow("scope", dStack)
            keyCode = cv2.waitKey(1)

            if cv2.getWindowProperty("scope", cv2.WND_PROP_VISIBLE) < 1:
                self.clientsocket.send(b"b")
                break
            self.clientsocket.send(b"g")

    def takeSnapshot(self):
        # grab the current timestamp and use it to construct the
        # output path
        ts = datetime.datetime.now()
        filename = "{}.jpg".format(ts.strftime("%Y-%m-%d_%H-%M-%S"))
        p = os.path.sep.join((self.outputPath, filename))

        # save the file
        cv2.imwrite(p, self.frame.copy())
        print("[INFO] saved {}".format(filename))

    def onClose(self):
        # set the stop event, cleanup the camera, and allow the rest of
        # the quit process to continue
        print("[INFO] closing...")
        self.stopEvent.set()
        self.root.quit()
