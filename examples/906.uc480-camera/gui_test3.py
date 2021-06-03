import tkinter
from tkinter import filedialog
from tkinter import colorchooser
import tkinter.ttk
import cv2
import PIL.Image, PIL.ImageTk
import time
from pyrolab.api import locate_ns, Proxy
import numpy as np
import socket
import pickle
import time
from datetime import datetime
import threading
import os

HEADERSIZE = 10
BRIGHTNESS = 5
PORT = 2222
SER_NUMBER_1 = 4103257229
SER_NUMBER_2 = 4103238947

class App:
    def __init__(self, window, window_title, video_source=0):
        self.window = window
        self.window.title(window_title)
        self.video_source = video_source
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)
        #self.window.geometry("700x700")
        self.directory = "C:/UC480Camera"

        # open video source (by default this will try to open the computer webcam)
        self.vid_1 = MyVideoCapture(self.video_source,SER_NUMBER_1)
        self.vid_2 = MyVideoCapture(self.video_source,SER_NUMBER_2)

        # Create a canvas that can fit the above video source size

        # Button that lets the user take a snapshot

        self.frame_1 = tkinter.Frame()
        #self.frame_1.pack(fill=tkinter.BOTH, expand=True)
        self.frame_1.grid(row=0, column=0)

        self.frame_1.columnconfigure(1, weight=1)
        self.frame_1.columnconfigure(3, pad=7)
        self.frame_1.rowconfigure(6, weight=1)
        self.frame_1.rowconfigure(8, pad=7)

        self.canvas_1 = tkinter.Canvas(self.frame_1, width = self.vid_1.width, height = self.vid_1.height)
        #self.canvas.pack()
        self.canvas_1.grid(row=0, column=0, columnspan=2, rowspan=7,
            padx=5, sticky=tkinter.E+tkinter.W+tkinter.S+tkinter.N)

        self.pic_btn_1 = tkinter.Button(self.frame_1, text="Snapshot", command=self.snapshot_1)
        self.pic_btn_1.grid(row=0, column=3, pady=4, sticky=tkinter.W)

        self.rec_btn_1 = tkinter.Button(self.frame_1, text="Record", command=self.record_1)
        self.rec_btn_1.grid(row=1, column=3, pady=4, sticky=tkinter.W)

        self.expo_lbl_1 = tkinter.Label(self.frame_1, text="Exposure:")
        self.expo_lbl_1.grid(row=4, column=3, pady=4)

        self.expo_slider_1 = tkinter.Scale(self.frame_1, from_=0, to=30,command=self.set_exposure_1)
        self.expo_slider_1.set(15)
        self.expo_slider_1.grid(row=5, column=3, pady=4, sticky=tkinter.W)

        self.color_1 = tkinter.IntVar()
        self.color_check_1 = tkinter.Checkbutton(self.frame_1, text='Color',variable=self.color_1, onvalue=1, offvalue=0, command=self.set_color_1)
        self.color_check_1.grid(row=2,column=3,pady=4)

        self.col_btn_1 = tkinter.Button(self.frame_1, text="Filter", command=self.select_filter_1)
        self.col_btn_1.grid(row=3, column=3, pady=4, sticky=tkinter.W)

        self.brow_btn_1 = tkinter.Button(self.frame_1, text="Browse", command=self.browse_files)
        self.brow_btn_1.grid(row=8, column=0, padx=5)

        self.file_lbl_1 = tkinter.Label(self.frame_1, text="File Selected:")
        self.file_lbl_1.grid(row=8,column=1,padx=5,sticky=tkinter.W)

        #self.sep = tkinter.ttk.Separator(self.frame, orient=tkinter.VERTICAL).grid(column=4, row=0, rowspan=8, sticky='ns')

        self.frame_2 = tkinter.Frame()
        #self.frame_2.pack(fill=tkinter.BOTH, expand=True)
        self.frame_2.grid(row=0, column=1)

        self.frame_2.columnconfigure(1, weight=1)
        self.frame_2.columnconfigure(3, pad=7)
        self.frame_2.rowconfigure(6, weight=1)
        self.frame_2.rowconfigure(7, pad=7)

        self.canvas_2 = tkinter.Canvas(self.frame_2, width = self.vid_2.width, height = self.vid_2.height)
        #self.canvas.pack()
        self.canvas_2.grid(row=0, column=0, columnspan=2, rowspan=7,
            padx=5, sticky=tkinter.E+tkinter.W+tkinter.S+tkinter.N)

        self.pic_btn_2 = tkinter.Button(self.frame_2, text="Snapshot", command=self.snapshot_2)
        self.pic_btn_2.grid(row=0, column=3, pady=4, sticky=tkinter.W)

        self.rec_btn_2 = tkinter.Button(self.frame_2, text="Record", command=self.record_2)
        self.rec_btn_2.grid(row=1, column=3, pady=4, sticky=tkinter.W)

        self.expo_lbl_2 = tkinter.Label(self.frame_2, text="Exposure:")
        self.expo_lbl_2.grid(row=4, column=3, pady=4)

        self.expo_slider_2 = tkinter.Scale(self.frame_2, from_=0, to=30,command=self.set_exposure_2)
        self.expo_slider_2.set(15)
        self.expo_slider_2.grid(row=5, column=3, pady=4, sticky=tkinter.W)

        self.color_2 = tkinter.IntVar()
        self.color_check_2 = tkinter.Checkbutton(self.frame_2, text='Color',variable=self.color_2, onvalue=1, offvalue=0, command=self.set_color_2)
        self.color_check_2.grid(row=2,column=3,pady=4)

        self.col_btn_2 = tkinter.Button(self.frame_2, text="Filter", command=self.select_filter_2)
        self.col_btn_2.grid(row=3, column=3, pady=4, sticky=tkinter.W)

        self.brow_btn_2 = tkinter.Button(self.frame_2, text="Browse", command=self.browse_files)
        self.brow_btn_2.grid(row=8, column=0, padx=5)

        self.file_lbl_2 = tkinter.Label(self.frame_2, text="File Selected:")
        self.file_lbl_2.grid(row=8,column=1,padx=5,sticky=tkinter.W)

        self.frame_3 = tkinter.Frame()
        #self.frame_3.pack(fill=tkinter.BOTH, expand=True)
        self.frame_3.grid(row=3, column=0,columnspan=1,rowspan=1)

        self.left_btn = tkinter.Button(self.frame_3, text="Left")
        self.left_btn.grid(row=0, column=1, pady=4)

        self.right_btn = tkinter.Button(self.frame_3, text="Right")
        self.right_btn.grid(row=0, column=2, pady=4)

        # After it is called once, the update method will be automatically called every delay milliseconds
        self.delay = 15
        self.update()

        self.window.mainloop()

    def select_filter_1(self):
        color_code = colorchooser.askcolor(title ="Choose color")
        self.filter = color_code[0]
        self.vid_1.set_filter(self.filter)

    def set_color_1(self):
        col = False
        if(self.color_1.get() == 1):
            col = True
        self.vid_1.set_color(col)

    def set_exposure_1(self,value):
        self.exposure_1 = int(value)
        self.vid_1.set_exposure(self.exposure_1)

    def browse_files(self):
        self.directory = filedialog.askdirectory()
      
        # Change label contents
        self.file_lbl_1.configure(text="File Selected: "+self.directory)
        self.file_lbl_2.configure(text="File Selected: "+self.directory)

    def record_1(self):
        if(self.rec_btn_1['text'] == "Record"):
            self.vid_1.set_rec_state(1,self.directory)
            self.rec_btn_1.configure(text="Stop")
        else:
            self.vid_1.set_rec_state(0,self.directory)
            self.rec_btn_1.configure(text="Record")

    def snapshot_1(self):
        # Get a frame from the video source
        self.vid_1.capture(self.directory)
    
    def select_filter_2(self):
        color_code = colorchooser.askcolor(title ="Choose color")
        self.filter = color_code[0]
        self.vid_2.set_filter(self.filter)

    def set_color_2(self):
        col = False
        if(self.color_2.get() == 1):
            col = True
        self.vid_2.set_color(col)

    def set_exposure_2(self,value):
        self.exposure_2 = int(value)
        self.vid_2.set_exposure(self.exposure_2)

    def record_2(self):
        if(self.rec_btn_2['text'] == "Record"):
            self.vid_2.set_rec_state(1,self.directory)
            self.rec_btn_2.configure(text="Stop")
        else:
            self.vid_2.set_rec_state(0,self.directory)
            self.rec_btn_2.configure(text="Record")

    def snapshot_2(self):
        # Get a frame from the video source
        self.vid_2.capture(self.directory)

    def update(self):
        # Get a frame from the video source
        ret_1, frame_1 = self.vid_1.get_frame()
        ret_2, frame_2 = self.vid_2.get_frame()

        if ret_1:
            self.photo_1 = PIL.ImageTk.PhotoImage(image = PIL.Image.fromarray(frame_1))
            self.canvas_1.create_image(0, 0, image = self.photo_1, anchor = tkinter.NW)
        if ret_2:
            self.photo_2 = PIL.ImageTk.PhotoImage(image = PIL.Image.fromarray(frame_2))
            self.canvas_2.create_image(0, 0, image = self.photo_2, anchor = tkinter.NW)

        self.window.after(self.delay, self.update)
    
    def close_window(self):
        self.window.destroy()
        self.vid_1.__del__()
        self.vid_2.__del__()


class MyVideoCapture:
    def __init__(self, video_source=0,ser_num=0):
        self.vs = video_source
        if(video_source == 0):
            # Open the video source
            self.vid = cv2.VideoCapture(video_source)
            if not self.vid.isOpened():
                raise ValueError("Unable to open video source", video_source)

            # Get video source width and height
            self.width = self.vid.get(cv2.CAP_PROP_FRAME_WIDTH)
            self.height = self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT)
        else:
            self.live = False
            self.color = False
            self.stop_video = threading.Event()
            self.ser_num = ser_num
            self.exposure = 3.16
            self.filter = (255,255,255)
            self.width = 640
            self.height = 512
            self.terminate = False
            self.rec_state = 0
            self.cap_state = 0
            self.init_camera()
            self.stopEvent = threading.Event()
            self.thread = threading.Thread(target=self.videoLoop, args=())
            self.thread.start()
            while(True):
                time.sleep(0.001)
                if(self.live == True):
                    break
    def set_filter(self,filter):
        if(filter != None):
            self.filter = filter
    def set_color(self,color):
        self.cam.color_gray(color)

    def set_exposure(self,exposure):
        self.exposure = (pow(10.0,(exposure+20.0)/10.0))/1000.0
        self.cam.set_exposure(self.exposure)
    
    def capture(self,directory):
        if not os.path.exists(directory+"/images"):
            os.makedirs(directory+"/images")
        self.cap_state = 1
        self.directory = directory

    def set_rec_state(self,state,directory):
        if(state == 1):
            if not os.path.exists(directory+"/videos"):
                os.makedirs(directory+"/videos")
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.out = cv2.VideoWriter(directory+"/videos/video-" + time.strftime("%d-%m-%Y-%H-%M-%S") + ".avi",fourcc, self.frame_rate, (640,512))
        else:
            self.out.release()
        self.rec_state = state

    
    def init_camera(self):
        ns = locate_ns(host="camacholab.ee.byu.edu")
        objs = str(ns.list())
        while(True):
            temp_str = objs[objs.find('\'')+1:-1]
            temp_obj = temp_str[0:temp_str.find('\'')]
            if(temp_obj[0:5] ==  "UC480"):
                temp_ser_no = int(temp_obj[6:len(temp_obj)])
                if(temp_ser_no == self.ser_num):
                    cam_str = temp_obj
            if(objs.find(',') == -1):
                break
            objs = objs[objs.find(',')+1:-1]
        try:
            cam_str
        except NameError:
            raise Exception("Camera with serial number " + str(self.ser_num) + " could not be found")
        self.cam = Proxy(ns.lookup(cam_str))

        self.cam.start(exposure=65)
        ip_address = self.cam.start_capture(self.color)
        self.clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clientsocket.connect((str(ip_address), PORT))

        self.time_s = 0
        self.frame_rate = 0
        self.count = -1

    def bayer_convert(self,bayer):
        if(self.color):
            ow = (bayer.shape[0]//4) * 4
            oh = (bayer.shape[1]//4) * 4

            R  = bayer[0::2, 0::2]
            B  = bayer[1::2, 1::2]
            G0 = bayer[0::2, 1::2]
            G1 = bayer[1::2, 0::2]
            G = G0[:oh,:ow]//2 + G1[:oh,:ow]//2
            bayer_R = np.array(R, dtype=np.uint8).reshape(512, 640)
            bayer_G = np.array(G, dtype=np.uint8).reshape(512, 640)
            bayer_B = np.array(B, dtype=np.uint8).reshape(512, 640)

            dStack = np.clip(np.dstack((bayer_B*(BRIGHTNESS/5),bayer_G*(BRIGHTNESS/5),bayer_R*(BRIGHTNESS/5))),0,255).astype('uint8')
        else:
            bayer_T = np.array(bayer, dtype=np.uint8).reshape(512, 640)
            dStack = np.clip((np.dstack(((bayer_T*(self.filter[2]/255))*(BRIGHTNESS/5),(bayer_T*(self.filter[1]/255))*(BRIGHTNESS/5),(bayer_T*(self.filter[0]/255))*(BRIGHTNESS/5)))),0,255).astype('uint8')
            #dStack = np.clip((np.dstack(((0.469 + bayer_T*0.75 - (bayer_T^2)*0.003)*(BRIGHTNESS/5),(bayer_T*0.95)*(BRIGHTNESS/5),(0.389 + bayer_T*1.34 - (bayer_T^2)*0.004)*(BRIGHTNESS/5)))),0,255).astype('uint8')
        #dStack = np.clip(np.dstack((bayer,bayer,bayer)),0,255).astype('uint8')
        return dStack

    def videoLoop(self):
        while not self.stop_video.is_set():
            if(self.count >= 0):
                t = time.time() - self.time_s
                self.frame_rate = (self.frame_rate*self.count + 1/t)/(self.count + 1)  

            self.time_s = time.time()
            if(self.count < 50):
                self.count = self.count + 1
            else:
                self.count = 1

            msg = b''
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

            if(imList.size == 327680):
                self.color = False
                self.count = 0
            else:
                self.color = True  
                self.count = 0                
            dStack = self.bayer_convert(imList)

            if(self.cap_state == 1):
                cv2.imwrite(self.directory+"/images/frame-" + time.strftime("%d-%m-%Y-%H-%M-%S") + ".jpg", dStack)
                self.cap_state = 0

            if(self.rec_state == 1):
                self.out.write(dStack)

            self.frame = cv2.cvtColor(dStack, cv2.COLOR_BGR2RGB)
            
            if(self.terminate == True):
                self.clientsocket.send(b'b')  
                self.live = False   
                break
            self.clientsocket.send(b'g')
            self.live = True

    def get_frame(self):
        if(self.vs == 0):
            if self.vid.isOpened():
                ret, frame = self.vid.read()
                if ret:
                    # Return a boolean success flag and the current frame converted to BGR
                    return (ret, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                else:
                    return (ret, None)
            else:
                return (ret, None)
        else:
            return(True, self.frame)


    # Release the video source when the object is destroyed
    def __del__(self):
        if(self.vs == 0):
            if self.vid.isOpened():
                self.vid.release()
        else:
            self.terminate = True
            while(True):
                time.sleep(0.001)
                if(self.live == False):
                    break
            self.cam.close()
            self.stop_video.set()
            try:
                self.out.release()
            except AttributeError:
                pass
            

# Create a window and pass it to the Application object
App(tkinter.Tk(), "PyroLab",1)