# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Pure Photonics Tunable Laser 5xx (specifically designed for PPCL550 and PPCL551)
-----------------------------------------------
Driver for the Santec PPCL-5xx Tunable Laser.
Author: David Hill (https://github.com/hillda3141)
Repo: https://github.com/BYUCamachoLab/pyrolab/pyrolab/drivers/lasers
Functions
---------
    __init__(self,minWL=1515,maxWL=1570,minPow=7,maxPow=13.5)
    start(self,port,baudrate=9600)
    setPower(self,power)
    setChannel(self,channel=1)
    setMode(self,mode)
    setWavelength(self,wavelength,jump=0)
    on(self,pin=13)
    off(self,pin=13)
    _communicate(self,register,data,rw)
    _send(self,msg)
    _recieve(self)
    _checksum(self,msg)
    _wl_freq(self,unit)
    close(self)
    __del__(self)
"""

import serial
import time
import threading
import array
from Pyro5.errors import PyroError
from Pyro5.api import expose
import pyrolab.api

C_SPEED = 299792458

ITLA_NOERROR=0x00
ITLA_EXERROR=0x01
ITLA_AEERROR=0x02
ITLA_CPERROR=0x03
ITLA_NRERROR=0x04
ITLA_CSERROR=0x05
ITLA_ERROR_SERPORT=0x01
ITLA_ERROR_SERBAUD=0x02

REG_Nop=0x00
REG_Mfgr=0x02
REG_Model=0x03
REG_Serial=0x04
REG_Release=0x06
REG_Gencfg=0x08
REG_AeaEar=0x0B
REG_Iocap=0x0D
REG_Ear=0x10
REG_Dlconfig=0x14
REG_Dlstatus=0x15
REG_Channel=0x30
REG_Power=0x31
REG_Resena=0x32
REG_Grid=0x34
REG_Fcf1=0x35
REG_Fcf2=0x36
REG_Oop=0x42
REG_Opsl=0x50
REG_Opsh=0x51
REG_Lfl1=0x52
REG_Lfl2=0x53
REG_Lfh1=0x54
REG_Lfh2=0x55
REG_Currents=0x57
REG_Temps=0x58
REG_Ftf=0x62
REG_Mode=0x90
REG_PW=0xE0
REG_Csweepsena=0xE5
REG_Csweepamp=0xE4
REG_Cscanamp=0xE4
REG_Cscanon=0xE5
REG_Csweepon=0xE5
REG_Csweepoffset=0xE6
REG_Cscanoffset=0xE6
REG_Cscansled=0xF0
REG_Cscanf1=0xF1
REG_Cscanf2=0xF2
REG_CjumpTHz=0xEA
REG_CjumpGHz=0xEB
REG_CjumpSled=0xEC
REG_Cjumpon=0xED
REG_Cjumpoffset=0xE6

READ=0
WRITE=1

@expose
class PPCL55x:

    def __init__(self,minWL=1515,maxWL=1570,minPow=7,maxPow=13.5):
        """"
        Initialize limiting values for the laser.

        Parameters
        ----------
        minWL : double
            Minimum wavelength the laser will produce in nanometers.
        maxWL : double
            Maximum wavelength the laser will produce in nanometers.
        minPow : double
            Minimum power level of the laser in dBm
        maxPow : double
            Maximum power level of the laser in dBm
        """
        self._activated = True
        self.minWavelength = minWL
        self.maxWavelength = maxWL
        self.minPower = minPow
        self.maxPower = maxPow
        self._error=ITLA_NOERROR
        self.latestregister = 0
        self.queue = []
        self.maxrowticket = 0
        pass


    def start(self,port,baudrate=9600):
        """"
        Connect with the laser via the serial port specified.

        Parameters
        ----------
        port : string
            Name of the port that the laser is connected to
        baudrate : int
            baudrate that the laser will use to communicate serially
        
        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")

        reftime = time.time()
        connected=False
        try:
            self.lasercom = serial.Serial(port,baudrate,timeout=1,parity=serial.PARITY_NONE)    #attempt connection with given baudrate
        except serial.SerialException:
            return(ITLA_ERROR_SERPORT)
        baudrate2=4800
        while baudrate2<115200: #if the initial connection doesn't work try different baudrates
            back = self._communicate(REG_Nop,0,0)
            if back != ITLA_NOERROR:
                #go to next baudrate
                if baudrate2==4800: baudrate2=9600
                elif baudrate2==9600: baudrate2=19200
                elif baudrate2==19200: baudrate2=38400
                elif baudrate2==38400: baudrate2=57600
                elif baudrate2==57600: baudrate2=115200
                self.lasercom.close()
                self.lasercom = serial.Serial(port,baudrate2,timeout=None,parity=serial.PARITY_NONE)            
            else:
                return(ITLA_NOERROR)
        print(baudrate2)
        self.lasercom.close()
        return(ITLA_ERROR_SERBAUD)


    def setPower(self,power):
        """"
        Set the power on the laser.

        Parameters
        ----------
        power : double
            Power that the laser will be set to in dBm
        
        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")

        sendPower = int(power*100)  #scale the power inputed
        back = self._communicate(REG_Power,sendPower,1)  #on the REG_Power register, send the power
        return back


    def setChannel(self,channel=1):
        """"
        Set the channel (should always be 1)

        Parameters
        ----------
        channel : int
            channel that the laser is on
        
        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")

        back = self._communicate(REG_Channel,channel,1)  #on the REG_Channel register, send the channel
        return back

    
    def setMode(self,mode):
        """
        Set the mode of operation for the laser

        Parameters
        ----------
        mode : int
            Mode for the laser:
            0 - regular mode
            1 - no dither mode
            2 - clean mode
        
        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")

        back = self._communicate(REG_Mode,mode,1)    #on the REG_Mode register, send the mode
        return back


    def sweep(self,minWL,maxWL,pause=0.3,timetaken=10):
        """
        Sweep the wavelength on the range inputed, for the time inputed

        Parameters
        ----------
        minWL : double
            starting wavelength (smallest) in nm
        maxWL : double
            ending wavelength (largest) in nm
        pause : double
            time between wavelength changes
        timetaken : double
            total time of the sweep
        
        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")

        number = int(timetaken/pause) + 1   #calculate the number of steps based on the pause length and time the sweep takes
        step = int((maxWL - minWL)/number)  #calculate the step size given the number of steps
        for count in range(number): #for each step
            currWL = min(minWL + count*step,maxWL)  #calculate the wavelength desired
            self.setWavelength(currWL,jump=1)   #set the wavelength
            time.sleep(pause)   #pause for the time wanted


    def setWavelength(self,wavelength,jump=False):
        """
        Set the wavelength of the laser

        Parameters
        ----------
        wavelength : double
            Wavelength of the laser
        jump : boolean
            Variable to define if the laser is currently on
            False - laser is off and normal method of setting the wavelength can be used
            True - laser is on and "clean jump" must be used *note that not all firmware supports clean jump*
        
        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")

        init_time = time.time()
        if(wavelength < self.minWavelength or wavelength > self.maxWavelength): #if the wavelength is not in the allowed range
                return "wavelength not in range"
        freq = self._wl_freq(wavelength)
        freq_t = int(freq/1000)
        freq_g = int(freq*10) - freq_t*10000    #convert the wavelength to frequency for each register
        print(freq_t)
        print(freq_g)

        if jump == False:   #if the laser is currently off, use a certain register
            back = self._communicate(REG_Fcf1,freq_t,1)
            if(back == ITLA_NOERROR):
                back = self._communicate(REG_Fcf2,freq_g,1)  #write the new wavelength to the REG_Fcf2 register
            time_diff = time.time() - init_time
            print(time_diff)
            return back
        if jump == True:   #if the laser is currently on, use a different register
            back = self._communicate(REG_CjumpTHz,freq_t,1)
            if(back == ITLA_NOERROR):
                back = self._communicate(REG_CjumpGHz,freq_g,1)  #write the new wavelength to the REG_CjumpGHz register
            if(back == ITLA_NOERROR):
                back == self._communicate(REG_Cjumpon,1,1)
            time_diff = time.time() - init_time
            print(time_diff)
            return back
    

    def on(self):
        """
        Turn on the laser

        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")

        back = self._communicate(REG_Resena,8,1) #start communication by sending 8 to REG_Resena register
        for x in range(10):
            back = self._communicate(REG_Nop,0,0)    #send 0 to REG_Nop register to wait for a "ready" response
        return back
    

    def off(self):
        """
        Turn off the laser

        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")

        back = self._communicate(REG_Resena,0,1) #stop communication by sending 0 to REG_Resena register
        return back


    def _communicate(self,register,data,rw):
        """
        Function that implements the commmunication with the laser. It will first send a message then recieve a response.

        Parameters
        ----------
        register : byte
            Register to which will be written. Each laser function has its own register.
        data : byte
            User-specific data that will be sent to the laser
        rw : int
            Defines if the communication is read-write or only write
            0 : write only
            1 : write then read
        
        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")

        lock = threading.Lock()
        lock.acquire()
        rowticket = self.maxrowticket + 1
        self.maxrowticket = self.maxrowticket + 1
        self.queue.append(rowticket)
        lock.release()
        while self.queue[0] != rowticket:
            rowticket=rowticket
        if rw == 0:     #if write and then read
            byte2 = int(data/256)
            byte3 = int(data - byte2*256)
            self.latestregister = register      #modify bytes for sending
            msg = [rw,register,byte2,byte3]
            msg[0] = msg[0] | int(self._checksum(msg))*16    #calculate checksum
            self._send(msg)  #send the message
            recvmsg = self._recieve()    #recieve the response from the laser
            #print(recvmsg)
            datamsg = recvmsg[2]*256 + recvmsg[3]
            if (recvmsg[0] & 0x03) == 0x02:     #if the message is larger than 4 bytes, read it using AEA method (not implemented)
                extmsg = self.AEA(datamsg)  #not implemented
                lock.acquire()
                self.queue.pop(0)
                lock.release()
                return extmsg
            lock.acquire()
            self.queue.pop(0)
            lock.release()
            errorMsg = int(recvmsg[0] & 0x03)
            return(errorMsg)
        else:   #if only write
            byte2=int(data/256)
            byte3=int(data - byte2*256)
            msg = [rw,register,byte2,byte3]
            msg[0] = msg[0] | int(self._checksum(msg))*16    #construct message and send
            self._send(msg)
            recvmsg = self._recieve()    #recieve message
            print("recieved")
            lock.acquire()
            self.queue.pop(0)
            lock.release()
            errorMsg = int(recvmsg[0] & 0x03)
            return(errorMsg)

    """
    Function sends message of four bytes to the laser.
    """
    def _send(self,msg):
        """
        Sends message of four bytes to the laser

        Parameters
        ----------
        msg : 4 x 1 bytes
            Message that will be sent to the laser
        
        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")

        self.lasercom.flush()
        print(f"Sent msg: {msg}")
        sendBytes = array.array('B',msg).tobytes()  #construct the bytes from the inputed message
        self.lasercom.write(sendBytes)  #write the bytes on the serial connection


    def _recieve(self):
        """
        Recieves, decifers, and certifies message from the laser
        
        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        PyroError(f"SerialCommunicationFailure queue[0] = {self.queue[0]}")
            Error to signal that the laser did not respond or the response was not long enough.
        PyroError("ChecksumError")
            Error to signal that the recieved message had an irregular checksum.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")

        reftime = time.time()
        while self.lasercom.inWaiting()<4:  #wait until 4 bytes are recieved
            if(time.time() > reftime + 0.5):   #if it takes longer than 0.25 seconds break
                self._error=ITLA_NRERROR
                return(0xFF,0xFF,0xFF,0xFF)
            time.sleep(0.0001)
        try:
            num = self.lasercom.inWaiting() #get number of bytes for debugging purposes
            print(num)
            msg = []
            bAll = self.lasercom.read(num)  #read the four bytes from serial
            print(bAll)
            for b in bAll:
                msg.append(b)   #construct array of bytes from the message
            msg = msg[0:4]
        except:
            raise PyroError(f"SerialCommunicationFailure queue[0] = {self.queue[0]}")
            msg = [0xFF,0xFF,0xFF,0xFF]
        print(f"Recieved msg: {msg}")
        if self._checksum(msg) == msg[0] >> 4:   #insure the checksum is correct
            self._error = msg[0] & 0x03
            return(msg) #return the message recieved
        else:
            raise PyroError("ChecksumError")     #if the checksum is wrong, log a CS error
            self._error=ITLA_CSERROR
            return(msg)  

    """
    Function calculates the checksum.
    """
    def _checksum(self,msg):     #calculate checksum
        """
        Calculate the checksum of a message

        Parameters
        ----------
        msg : 4 x 1 bytes
            Four-byte message that will be used to produce a checksum
        
        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")

        bip8=(msg[0] & 0x0f) ^ msg[1] ^ msg[2] ^ msg[3]
        bip4=((bip8 & 0xf0) >> 4) ^ (bip8 & 0x0f)
        return bip4

    """
    Convert from wavelength to frequency
    """
    def _wl_freq(self,wl):
        """
        Convert from wavelength to frequency using propagation velocity of c

        Parameters
        ----------
        wl : double
            Wavelength in nanometers
        
        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")

        return C_SPEED/wl
    

    def close(self):
        """
        Disconnect from the laser

        Raises
        ------
        PyroError("DeviceLockedError")
            Error to signal that the constuctor was not called and therefore the device is locked.
        """
        try:
            self._activated
        except AttributeError:
            raise PyroError("DeviceLockedError")

        self.lasercom.close()
        return 0

    def __del__(self):
        """"
        Function called when Proxy connection is lost.
        """
        self.close()