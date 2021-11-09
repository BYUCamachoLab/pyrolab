from ctypes import *
import numpy as np
import os
import time
import cv2
os.add_dll_directory("C:\\Program Files\\Thorlabs\\Scientific Imaging\\ThorCam\\")

from thorlabs_kinesis import thor_science_camera as tc
import sys
np.set_printoptions(threshold=sys.maxsize)

COLOR = True
BRIGHTNESS = 10
PIXEL_MAX = 2023

class Camera():

    def bayer_convert(self,bayer):
        """
        Coverts the raw data to something that can be displayed on-screen.

        Parameters
        ----------
        bayer : numpy array
            this is the raw data that is recieved from the camera    
        """
        # global mask

        if(COLOR):  #if the data is in color, put the numpy array into BGR form
            # if(not mask.any()):
            #     mask = _generate_mask(bayer.shape,4)
            
            frame_height = bayer.shape[0]//2
            # print(frame_height)
            frame_width = bayer.shape[1]//2
            # print(frame_width)

            ow = (bayer.shape[0]//4) * 4
            # print(ow)
            oh = (bayer.shape[1]//4) * 4
            # print(oh)

            # print(bayer)

            R  = bayer[0::2, 0::2]
            # print(R)
            B  = bayer[1::2, 1::2]
            # print(B)
            G0 = bayer[0::2, 1::2]
            G1 = bayer[1::2, 0::2]
            G = G0[:oh,:ow]//2 + G1[:oh,:ow]//2
            # print(G)

            bayer_R = np.array(R, dtype=np.uint8).reshape(frame_height, frame_width)
            bayer_G = np.array(G, dtype=np.uint8).reshape(frame_height, frame_width)
            bayer_B = np.array(B, dtype=np.uint8).reshape(frame_height, frame_width)

            # if(MASK_ON == True):
            #     idx=(mask==1)
            #     bayer_R[idx]=255
            #     bayer_G[idx]=255
            #     bayer_B[idx]=255

            dStack = np.clip(np.dstack((bayer_B*(BRIGHTNESS/5),bayer_G*(BRIGHTNESS/5),
                            bayer_R*(BRIGHTNESS/5))),0,PIXEL_MAX).astype('uint8')
        else:   #if the data is grayscale, put it into BGR form
            # if(not mask.any()):
            #     mask = _generate_mask((int(bayer.shape[0]*2),int(bayer.shape[1]*2)))
            frame_height = bayer.shape[0]
            frame_width = bayer.shape[1]
            bayer_T = np.array(bayer, dtype=np.uint8).reshape(frame_height,
                            frame_width)

            # if(MASK_ON == True):
            #     idx=(mask==1)
            #     bayer_T[idx]=255

            dStack = np.clip((np.dstack(((bayer_T)*(BRIGHTNESS/5),
                            (bayer_T)*(BRIGHTNESS/5),(bayer_T)*(BRIGHTNESS/5)))),0,
                            PIXEL_MAX).astype('uint8')
        return dStack

    def __init__(self):
        ser_no = create_string_buffer(4096)
        length = c_int(4096)
        error = tc.OpenSDK()
        print(error)
        error = tc.DiscoverAvailableCameras(ser_no,length)
        print(error)
        print(ser_no.value)
        c_camera_handle = c_void_p()
        error = tc.OpenCamera(ser_no.value, c_camera_handle)
        print(error)

        print(c_camera_handle.value)
        error = tc.SetFramesPerTrigger(c_camera_handle,c_uint(0))
        print(error)
        exposure = c_longlong()
        error = tc.GetExposure(c_camera_handle,exposure)
        print(error)
        print(exposure)
        min_exposure = c_longlong()
        max_exposure = c_longlong()
        error = tc.GetExposureTimeRange(c_camera_handle,min_exposure,max_exposure)
        print(error)
        print(min_exposure)
        print(max_exposure)
        exposure = c_longlong(3000)
        error = tc.SetExposure(c_camera_handle,exposure)
        print(error)
        height = c_int()
        error = tc.GetImageHeight(c_camera_handle,height)
        print(error)
        print(height)
        width = c_int()
        error = tc.GetImageWidth(c_camera_handle,width)
        print(error)
        print(width)
        error = tc.ArmCamera(c_camera_handle,c_int(2))
        print(error)
        error = tc.IssueSoftwareTrigger(c_camera_handle)
        print(error)
        image_buffer = POINTER(c_ushort)()
        frame_count = c_int()
        metadata_pointer = POINTER(c_char)()
        metadata_size_in_bytes = c_int()
        time.sleep(5)
        t_init = time.time()

        while(True):    #loop to get frames
            error = tc.GetFrameOrNull(c_camera_handle, image_buffer, frame_count, metadata_pointer, metadata_size_in_bytes)
            # print(image_buffer)
            image_buffer._wrapper = self
            if(image_buffer):
                image_buffer_as_np_array = np.ctypeslib.as_array(image_buffer,shape=(1080,1440))
                # print(image_buffer_as_np_array.size)
                # print(image_buffer_as_np_array)
                # print(image_buffer_as_np_array)
                dStack = self.bayer_convert(image_buffer_as_np_array)
                # print(dStack.shape)
                # print(dStack)
                cv2.imshow('SCI_LOCAL',dStack)
                keyCode = cv2.waitKey(1)
                # time.sleep(0.5)
                pfs = 1.0/(time.time()-t_init)
                print("pfs: " + str(pfs))
                t_init = time.time()
                # break
            
            #if window is exited, break from the loop
            if cv2.getWindowProperty('SCI_LOCAL',cv2.WND_PROP_VISIBLE) < 1:
                break

        # # count = 0
        # error = tc.GetFrameOrNull(c_camera_handle, image_buffer, frame_count, metadata_pointer, metadata_size_in_bytes)
        # # print(image_buffer)
        # image_buffer._wrapper = self
        # if(image_buffer):
        #     image_buffer_as_np_array = np.ctypeslib.as_array(image_buffer,shape=(1080,1440))
        #     print(image_buffer_as_np_array.size)
        #     print(image_buffer_as_np_array)
        #     dStack = self.bayer_convert(image_buffer_as_np_array)
        #     print(dStack.shape)
        #     print(dStack)
        #     cv2.imshow('SCI_LOCAL',dStack)
        #     cv2.waitKey()
        error = tc.CloseCamera(c_camera_handle)
        print(error)
        error = tc.CloseSDK()
        print(error)
        

camera = Camera()



