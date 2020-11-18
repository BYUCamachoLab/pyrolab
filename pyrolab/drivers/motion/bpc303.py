# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Thorlabs 3-Channel 150V Benchtop Piezo Controller with USB (BPC303)
-----------------------------------------------
Driver for the Thorlabs BPC-303 Benchtop Piezo.
Author: David Hill (https://github.com/hillda3141)
Repo: https://github.com/BYUCamachoLab/pyrolab/blob/bpc303/pyrolab/drivers/motion

Warning
-------
Not all controllers support getting the maximum position. The default maximum position is 20 micrometers
and when 0 is returned by a device the maximum travel for that channel will be defaulted.
"""

from win32event import CreateMutex
from win32api import GetLastError
from winerror import ERROR_ALREADY_EXISTS
from sys import exit

handle = CreateMutex(None, 1, 'David Service')

if GetLastError() == ERROR_ALREADY_EXISTS:
    # Take appropriate action, as this is the second instance of this script.
    print('An instance of this application is already running.')
    exit(1)

from Pyro5.api import expose, locate_ns, Daemon, config, behavior

def get_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

import os
os.environ['PATH'] = "C:\\Program Files\\ThorLabs\\Kinesis" + ";" + os.environ['PATH']  #this path must be change to the location of the .dll files from Thorlabs

import time
from thorlabs_kinesis import benchtop_piezo as bp

from ctypes import (
    c_short,
    c_char_p,
    c_void_p,
    byref,
    c_int,
    create_string_buffer,
)
from ctypes.wintypes import (
    DWORD,
    WORD,
)

import pyrolab.api

SHORT_MAX = 32767

@expose
class BPC303:
    """ A Thorlabs BPC-303 Benchtop Piezo.
    Lasers can only be accessed by their serial port address.
    Attributes:
    ----------
    serialno : c_char_p
        serial number (stored as a c-type character array) for communicating with a BPC303
    pullPeriod : int
        the time between each consecutive data pull from the BPC303 (ms)
    xMax : int
        maximum travel for the first channel (nm)
    yMax : int
        maximum travel for the second channel (nm)
    zMax : int
        maximum travel for the third channel (nm)
    xHome : int
        home value for the first channel (nm)
    yHome : int
        home value for the second channel (nm)
    zHome : int
        home value for the third channel (nm)
    xCurr : int
        current position of the first channel (nm)
    yCurr : int
        current position of the second channel (nm)
    zCurr : int
        current position of the third channel (nm)
    """

    serialno = c_char_p(bytes("","utf-8"))  #serial number of the BPC303
    pullPeriod = 200    #time between data pull from the device

    xMax = 20000    #values for each axis maximum
    yMax = 20000
    zMax = 20000

    xHome = 10000     #home values
    yHome = 10000
    zHome = 10000

    xCurr = 0   #the value of each axis is stored in the program rather than retrieving it every time, this helps with moving precision
    yCurr = 0
    zCurr = 0

    def __init__(self):
        pass

    def set_serial(self,serial):
        self.serialno = c_char_p(bytes(str(serial),"utf-8"))

    def set_pull_period(self,period):
        self.pullPeriod = period

    def help(self):
        return "set_serial(serialNumber) - set the serial number that you will communicate with (do this first)\nstart() - initiate communication\nend() - end communication\nhome() - homes all three channels\nset_home(x,y,z) - set the home position for each channel\nzero(channel) - zero a specific channel\nzero_all() - zero all three channels\nset_pos(position,channel) - set the position of a specific channel (nm)\nmove_to(x,y,z) - set the position of all three channels (nm)\njog(stepSize,channel) - jog the position of a certain channel (nm)\njog_all(XstepSize,YstepSize,ZstepSize) - jog the position of all three channels (nm)\nget_pos(channel) - returns the position of a specific channel (nm)\nget_all() - returns the position of all three channels (nm), example x,y,z = bp.get_all()"

    def map_point(self,pos,channel):
        """
        map a position value to 0-SHORT_MAX which is the range of positions for serial communication
        """
        vol = 0
        if channel - bp.Channel1:
            vol = round(pos*SHORT_MAX/self.xMax) #if dealing with the x axis, map using xMax
        if channel - bp.Channel2:
            vol = round(pos*SHORT_MAX/self.yMax) #if dealing with the y axis, map using yMax
        if channel - bp.Channel2:
            vol = round(pos*SHORT_MAX/self.zMax) #if dealing with the z axis, map using zMax
        #print(vol)
        if(vol > SHORT_MAX):    #if the value is out of range, set to either max or min value
            vol = SHORT_MAX
        if(vol < 0):
            vol = 0
        #print(c_short(vol))
        return vol

    def map_vol(self,loc,channel):
        """
        map a serial-recieved value or voltage to 0-maxValue range of a given channel
        """
        point = 0
        vol = int(loc)
        if channel - bp.Channel1:
            point = round(vol*self.xMax/SHORT_MAX)   #depending on the channel, map the voltage to the position
        if channel - bp.Channel2:
            point = round(vol*self.yMax/SHORT_MAX)
        if channel - bp.Channel2:
            point = round(vol*self.zMax/SHORT_MAX)
        return point

    def check_serial(self):
        """
        checks to ensure there is a benchtop piezo device connected with that serial number
        """
        serialList = c_char_p(bytes("","utf-8"))
        bp.TLI_GetDeviceListByTypeExt(serialList, 250, 71)  # get list of serial numbers of benchtop-piezo devices connected
        for i in range(0,40,10):
            tempNum = (serialList.value[i:i+8]).decode("utf-8")
            if tempNum=="":
                return False
            if int(tempNum)==int((self.serialno.value[0:8]).decode("utf-8")):
                return True

    def open_serial(self):
        """
        opens serial communication and starts polling from the benchtop piezo
        """
        bp.PBC_Open(self.serialno)       # open the device for communication
        self.start_polling()

    def home(self):
        """
        homes all three axis
        """
        bp.PBC_SetPosition(self.serialno,bp.Channel1,self.xHome)    # set the position to the stored home values
        bp.PBC_SetPosition(self.serialno,bp.Channel2,self.yHome)
        bp.PBC_SetPosition(self.serialno,bp.Channel3,self.zHome)
        self.xCurr = self.map_vol(self.xHome,bp.Channel1)    # set the current position by maping the home values to position
        self.yCurr = self.map_vol(self.yHome,bp.Channel2)
        self.zCurr = self.map_vol(self.zHome,bp.Channel3)
        time.sleep(1)   #give it time to settle

    def set_home(self,x,y,z):
        """
        set a new home position for the axises
        """
        self.xHome =  self.map_point(x,bp.Channel1)   # set the new home values by maping the position to voltage
        self.yHome =  self.map_point(y,bp.Channel2)
        self.zHome =  self.map_point(z,bp.Channel3)

    def enable_channels(self):
        """
        enables communication with all three channels
        """
        bp.PBC_EnableChannel(self.serialno, bp.Channel1)
        bp.PBC_EnableChannel(self.serialno, bp.Channel2)
        bp.PBC_EnableChannel(self.serialno, bp.Channel3)

    def max_travel(self):
        """
        retrieves the max amount of movement for each axis
        """
        x = int(bp.PBC_GetMaxTravel(self.serialno,bp.Channel1))*100      #ask for the max travel of each axis
        if x > 0:       #if it returns zero, this function is not supported by the module and we use the default max value (20000)
            self.xMax = x
        y = int(bp.PBC_GetMaxTravel(self.serialno,bp.Channel2))*100
        if y > 0:
            self.yMax = y
        z = int(bp.PBC_GetMaxTravel(self.serialno,bp.Channel3))*100
        if z > 0:
            zMax = z
        #print(xMax,yMax,self.zMax)
        return self.xMax,self.yMax,self.zMax

    def zero(self,channel,pause=1):
        """
        zeros the given channel, if 0 is inputed at the end of the function call it will not pause 30 seconds
        """
        bp.PBC_SetZero(self.serialno, channel)
        if pause==1:
            time.sleep(25)

    def zero_all(self):
        """
        zeros all three axises
        """
        self.zero(bp.Channel1,0)
        self.zero(bp.Channel2,0)
        self.zero(bp.Channel3,0)
        time.sleep(25)  #pause to give it time

    def start_polling(self):
        """
        function starts polling data from device
        """
        bp.PBC_StartPolling(self.serialno,bp.Channel1,c_int(self.pullPeriod))    # start polling each channel every 200 ms
        bp.PBC_StartPolling(self.serialno,bp.Channel2,c_int(self.pullPeriod))
        bp.PBC_StartPolling(self.serialno,bp.Channel3,c_int(self.pullPeriod))
        bp.PBC_ClearMessageQueue(self.serialno)  # clear prior messages
        time.sleep(1)   # pause 1 sec
        bp.PBC_SetPositionControlMode(self.serialno,bp.Channel1,c_int(2))    #set the mode to closed operation
        bp.PBC_SetPositionControlMode(self.serialno,bp.Channel2,c_int(2))
        bp.PBC_SetPositionControlMode(self.serialno,bp.Channel3,c_int(2))
        time.sleep(0.5)

    def stop_polling(self):
        """
        stop polling data from device
        """
        bp.PBC_StopPolling(self.serialno,bp.Channel1)
        bp.PBC_StopPolling(self.serialno,bp.Channel2)
        bp.PBC_StopPolling(self.serialno,bp.Channel3)

    def disconnect(self):
        """
        disconnect from the device
        """
        done = 0
        for i in range(10):     #try up to 10 times to disconnect (it doesn't go through every so often)
            if bp.PBC_Disconnect(self.serialno) == 0:
                done = 1    #if we successfully disconnect, return 1
                break
            else:
                time.sleep(1)
        return done     #this will be 0 if we failed to disconnect

    def set_pos(self,pos,channel):
        """
        set the postion of a certain axis to the given position (nm), if not in the allowed range, set it to min or max value
        """
        bp.PBC_SetPosition(self.serialno,channel,self.map_point(pos,channel)) #map the point to voltage and set the position
        if channel == bp.Channel1:
            self.xCurr = self.map_vol(self.map_point(pos,channel),channel)
        if channel == bp.Channel2:
            self.yCurr = self.map_vol(self.map_point(pos,channel),channel)
        if channel == bp.Channel3:
            self.zCurr = self.map_vol(self.map_point(pos,channel),channel)
        time.sleep(0.5)

    def move_to(self,xPos,yPos,zPos):
        """
        set all three values (nm)
        """
        self.set_pos(xPos,bp.Channel1)
        self.set_pos(yPos,bp.Channel2)
        self.set_pos(zPos,bp.Channel3)

    def jog(self,step,channel):
        """
        set a channel's position to the current position plus the inputed step value (nm)
        """
        pos = 0
        if channel == bp.Channel1:
            pos = self.xCurr
        if channel == bp.Channel2:
            pos = self.yCurr
        if channel == bp.Channel3:
            pos = self.zCurr
        self.set_pos(pos + step,channel)

    def jog_all(self,xStep,yStep,zStep):
        """
        jog each axis by the inputed amounts
        """
        self.jog(xStep,bp.Channel1)
        self.jog(yStep,bp.Channel2)
        self.jog(zStep,bp.Channel3)
        #print("R-Point: (", self.xCurr, ",", self.yCurr, ",", self.zCurr, ")")

    def fine_tune(self):
        """
        moves the exact actual position of the channels to the "current positions"
        it can take a few seconds to fine tune the channels, as each channel is naturally off by 2-15 nm
        Warning: this is not based of the "zero" function
        """
        xTemp = self.xCurr
        yTemp = self.yCurr
        zTemp = self.zCurr
        while True:
            diff = self.xCurr-self.map_vol(bp.PBC_GetPosition(self.serialno,bp.Channel1),bp.Channel1)
            if diff==0:
                break
            xTemp += diff
            bp.PBC_SetPosition(self.serialno,bp.Channel1,self.map_point(xTemp,bp.Channel1))
            time.sleep(0.35)
        while True:
            diff = self.yCurr-self.map_vol(bp.PBC_GetPosition(self.serialno,bp.Channel2),bp.Channel2)
            if diff==0:
                break
            yTemp += diff
            bp.PBC_SetPosition(self.serialno,bp.Channel2,self.map_point(yTemp,bp.Channel2))
            time.sleep(0.35)
        while True:
            diff = self.zCurr-self.map_vol(bp.PBC_GetPosition(self.serialno,bp.Channel3),bp.Channel3)
            if diff==0:
                break
            zTemp += diff
            bp.PBC_SetPosition(self.serialno,bp.Channel3,self.map_point(zTemp,bp.Channel3))
            time.sleep(0.35)

    def get_pos(self,channel):
        """
        returns the current position of the inputed channel, as measured by the device (nm)
        """
        pos = bp.PBC_GetPosition(self.serialno,channel)  #get the voltage position and map it to an integer position (returns in nm)
        return self.map_vol(pos,channel)

    def get_all(self):
        """
        returns the current positions of each channel, as measured by the device (nm)
        """
        xPos = self.get_pos(bp.Channel1)
        yPos = self.get_pos(bp.Channel2)
        zPos = self.get_pos(bp.Channel3)
        return xPos,yPos,zPos

    def start(self):
        """
        open serial communication with the BCP303 and initialize values based on the device
        """
        if bp.TLI_BuildDeviceList() != 0:   #if there are errors building devices
            return 0
        if bp.TLI_GetDeviceListSize() == 0: #if there are no devices
            return 0
        if not self.check_serial():    #get the serial number of the BP303
            return 0
        self.open_serial()   #open communication
        self.enable_channels()
        self.max_travel()
        self.set_home(self.xMax/2,self.yMax/2,self.zMax/2)
        self.start_polling() #start polling data
        return 1

    def end(self):
        """
        close the communication channel with the BP303
        """
        self.stop_polling()
        dis = self.disconnect()  #attempt to disconnect, if unsuccessful return 0
        bp.PBC_Close(self.serialno)
        return dis


if __name__ == "__main__":
    config.HOST = get_ip()
    config.SERVERTYPE = "multiplex"
    daemon = Daemon()
    ns = locate_ns(host="camacholab.ee.byu.edu")

    uri = daemon.register(BPC303)
    ns.register("BPC303", uri)
    try:
        daemon.requestLoop()
    finally:
        ns.remove("BPC303")