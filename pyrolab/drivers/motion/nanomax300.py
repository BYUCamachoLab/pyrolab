# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
PRM1Z8
------

Submodule containing drivers for the ThorLabs NanoMax 300 piezo controlled
motion stage.

Author: Sequoia Ploeg (https://github.com/sequoiap)
Repo: https://github.com/BYUCamachoLab/pyrolab
"""

from pyrolab.drivers.motion import Motion
from pyrolab.drivers.motion._kinesis.bpc303 import BPC303
from pyrolab.api import expose


SHORT_MAX = 32767


@expose
class NanoMax300(Motion, BPC303):
    """
    A NanoMax 300 stage controlled by a BPC303 piezo controller.

    Parameters
    ----------
    serialno : int
        The serial number of the device to connect to.
    polling : int
        The polling rate in milliseconds.
    
    Attributes
    ----------
    xMax : int
        Maximum travel for the first channel (nm)
    yMax : int
        Maximum travel for the second channel (nm)
    zMax : int
        Maximum travel for the third channel (nm)
    xHome : int
        Home value for the first channel (nm)
    yHome : int
        Home value for the second channel (nm)
    zHome : int
        Home value for the third channel (nm)
    xCurr : int
        Current position of the first channel (nm)
    yCurr : int
        Current position of the second channel (nm)
    zCurr : int
        Current position of the third channel (nm)
    """

    """
    home() - homes all three channels\n
    set_home(x,y,z) - set the
    home position for each channel\n
    set_pos(position,channel) -
    set the position of a specific channel (nm)\n
    move_to(x,y,z) - set the
    position of all three channels (nm)\n
    jog(stepSize,channel) - jog the
    position of a certain channel (nm)\n
    jog_all(XstepSize,YstepSize,ZstepSize)
    - jog the position of all three channels (nm)\n
    get_pos(channel) - returns
    the position of a specific channel (nm)\n
    get_all() - returns the position
    of all three channels (nm), example x,y,z = bp.get_all()"
    """
    # Values for each axis maximum
    xMax = 20000
    yMax = 20000
    zMax = 20000

    # Home values
    xHome = 10000
    yHome = 10000
    zHome = 10000

    # The value of each axis is stored in the program rather than retrieving it
    # every time, this helps with moving precision
    xCurr = 0 
    yCurr = 0
    zCurr = 0
    def __init__(self, serialno, polling=200):
        super().__init__(serialno, polling)

    def connect(self):
        """
        Open serial communication with the BCP303 and initialize values based
        on the device.
        """
        
        self.set_home(self.xMax/2,self.yMax/2,self.zMax/2)
        return 1

    def map_point(self,pos,channel):
        """
        map a position value to 0-SHORT_MAX which is the range of positions for serial communication
        """
        vol = 0
        if channel - CHANNEL1:
            vol = round(pos*SHORT_MAX/self.xMax) #if dealing with the x axis, map using xMax
        if channel - CHANNEL2:
            vol = round(pos*SHORT_MAX/self.yMax) #if dealing with the y axis, map using yMax
        if channel - CHANNEL2:
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
        if channel - CHANNEL1:
            point = round(vol*self.xMax/SHORT_MAX)   #depending on the channel, map the voltage to the position
        if channel - CHANNEL2:
            point = round(vol*self.yMax/SHORT_MAX)
        if channel - CHANNEL2:
            point = round(vol*self.zMax/SHORT_MAX)
        return point

    def home(self):
        """
        homes all three axis
        """
        bp.PBC_SetPosition(self._serialno,CHANNEL1,self.xHome)    # set the position to the stored home values
        bp.PBC_SetPosition(self._serialno,CHANNEL2,self.yHome)
        bp.PBC_SetPosition(self._serialno,CHANNEL3,self.zHome)
        self.xCurr = self.map_vol(self.xHome,CHANNEL1)    # set the current position by maping the home values to position
        self.yCurr = self.map_vol(self.yHome,CHANNEL2)
        self.zCurr = self.map_vol(self.zHome,CHANNEL3)
        time.sleep(1)   #give it time to settle

    def set_home(self,x,y,z):
        """
        set a new home position for the axises
        """
        self.xHome =  self.map_point(x,CHANNEL1)   # set the new home values by maping the position to voltage
        self.yHome =  self.map_point(y,CHANNEL2)
        self.zHome =  self.map_point(z,CHANNEL3)

    def set_pos(self,pos,channel):
        """
        set the postion of a certain axis to the given position (nm), if not in the allowed range, set it to min or max value
        """
        bp.PBC_SetPosition(self._serialno,channel,self.map_point(pos,channel)) #map the point to voltage and set the position
        if channel == CHANNEL1:
            self.xCurr = self.map_vol(self.map_point(pos,channel),channel)
        if channel == CHANNEL2:
            self.yCurr = self.map_vol(self.map_point(pos,channel),channel)
        if channel == CHANNEL3:
            self.zCurr = self.map_vol(self.map_point(pos,channel),channel)
        time.sleep(0.5)

    def move_to(self,xPos,yPos,zPos):
        """
        set all three values (nm)
        """
        self.set_pos(xPos,CHANNEL1)
        self.set_pos(yPos,CHANNEL2)
        self.set_pos(zPos,CHANNEL3)

    def jog(self,step,channel):
        """
        set a channel's position to the current position plus the inputed step value (nm)
        """
        pos = 0
        if channel == CHANNEL1:
            pos = self.xCurr
        if channel == CHANNEL2:
            pos = self.yCurr
        if channel == CHANNEL3:
            pos = self.zCurr
        self.set_pos(pos + step,channel)

    def jog_all(self,xStep,yStep,zStep):
        """
        jog each axis by the inputed amounts
        """
        self.jog(xStep,CHANNEL1)
        self.jog(yStep,CHANNEL2)
        self.jog(zStep,CHANNEL3)
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
            diff = self.xCurr-self.map_vol(bp.PBC_GetPosition(self._serialno,CHANNEL1),CHANNEL1)
            if diff==0:
                break
            xTemp += diff
            bp.PBC_SetPosition(self._serialno,CHANNEL1,self.map_point(xTemp,CHANNEL1))
            time.sleep(0.35)
        while True:
            diff = self.yCurr-self.map_vol(bp.PBC_GetPosition(self._serialno,CHANNEL2),CHANNEL2)
            if diff==0:
                break
            yTemp += diff
            bp.PBC_SetPosition(self._serialno,CHANNEL2,self.map_point(yTemp,CHANNEL2))
            time.sleep(0.35)
        while True:
            diff = self.zCurr-self.map_vol(bp.PBC_GetPosition(self._serialno,CHANNEL3),CHANNEL3)
            if diff==0:
                break
            zTemp += diff
            bp.PBC_SetPosition(self._serialno,CHANNEL3,self.map_point(zTemp,CHANNEL3))
            time.sleep(0.35)

    def get_pos(self,channel):
        """
        returns the current position of the inputed channel, as measured by the device (nm)
        """
        pos = bp.PBC_GetPosition(self._serialno,channel)  #get the voltage position and map it to an integer position (returns in nm)
        return self.map_vol(pos,channel)

    def get_all(self):
        """
        returns the current positions of each channel, as measured by the device (nm)
        """
        xPos = self.get_pos(CHANNEL1)
        yPos = self.get_pos(CHANNEL2)
        zPos = self.get_pos(CHANNEL3)
        return xPos,yPos,zPos