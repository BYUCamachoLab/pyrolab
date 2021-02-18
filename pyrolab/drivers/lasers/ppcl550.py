# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Pure Photonics Tunable Laser 5xx (specifically designed for PPCL550 and PPCL551)
-----------------------------------------------
Driver for the Santec PPCL-5xx Tunable Laser.
Contributors
 * David Hill (https://github.com/hillda3141)
 * Sequoia Ploeg (https://github.com/sequoiap)
Repo: https://github.com/BYUCamachoLab/pyrolab
"""

import serial
import time
import struct
import sys
import threading
import array

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

    """ A Pure Photonics Laser.
    ----------
    latestregister : int
        stores the last register that was read or written
    queue : array<int>
        stores the errors that come back
    maxrowticket : int
        stores the placement for communication
    lasercom : serial.Serial()
        serial object for communication with the laser
    minWavelength : int
        minimum wavelength that the laser can be set to
    maxWavelength : int
        maximum wavelength that the laser can be set to
    minPower : int
        minimum power that the laser can be set to
    maxPower : int
        maximum power that the laser can be set to
    """

    latestregister = 0
    queue = []
    maxrowticket = 0
    lasercom = serial.Serial()
    minWavelength = 0
    maxWavelength = 0
    minPower = 0
    maxPower = 0

    _error=ITLA_NOERROR
    seriallock = 0
    """
    Initialize limiting values for the laser
    """
    def __init__(self,minWL=1515,maxWL=1570,minPow=7,maxPow=13.5):
        self.minWavelength = minWL
        self.maxWavelength = maxWL
        self.minPower = minPow
        self.maxPower = maxPow
        pass

    """
    Connect with the laser via the serial port specified
    """
    def connect(self,port,baudrate=9600):
        reftime = time.time()
        connected=False
        try:
            self.lasercom = serial.Serial(port,baudrate,timeout=1,parity=serial.PARITY_NONE)    #attempt connection with given baudrate
        except serial.SerialException:
            return(ITLA_ERROR_SERPORT)
        baudrate2=4800
        while baudrate2<115200: #if the initial connection doesn't work try different baudrates
            back = self.communicate(REG_Nop,0,0)
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

    """
    Disconnect from the laser
    """
    def disconnect(self):
        self.lasercom.close()
        return 0

    """
    Set the power on the laser.
    """
    def setPower(self,power):
        sendPower = int(power*100)  #scale the power inputed
        back = self.communicate(REG_Power,sendPower,1)  #on the REG_Power register, send the power
        return back

    """
    Set the channel (should always be 1)
    """
    def setChannel(self,channel=1):
        back = self.communicate(REG_Channel,channel,1)  #on the REG_Channel register, send the channel
        return back

    """
    Set the mode of operation for the laser
      0: regular mode
      1: no dither mode
      2: clean mode
    """
    def setMode(self,mode):
        back = self.communicate(REG_Mode,mode,1)    #on the REG_Mode register, send the mode
        return back

    """
    Sweep the wavelength on the range inputed, for the time inputed
    """
    def sweep(self,minWL,maxWL,pause=0.3,timetaken=10):
        number = int(timetaken/pause) + 1   #calculate the number of steps based on the pause length and time the sweep takes
        step = int((maxWL - minWL)/number)  #calculate the step size given the number of steps
        for count in range(number): #for each step
            currWL = min(minWL + count*step,maxWL)  #calculate the wavelength desired
            self.setWavelength(currWL,jump=1)   #set the wavelength
            time.sleep(pause)   #pause for the time wanted

    """
    initialize limiting values for the laser
    """
    def setWavelength(self,wavelength,jump=0):
        init_time = time.time()
        if(wavelength < self.minWavelength or wavelength > self.maxWavelength): #if the wavelength is not in the allowed range
                return "wavelength not in range"
        freq = self.wl_freq(wavelength)
        freq_t = int(freq/1000)
        freq_g = int(freq*10) - freq_t*10000    #convert the wavelength to frequency for each register
        print(freq_t)
        print(freq_g)

        if jump == 0:   #if the laser is currently off, use a certain register
            back = self.communicate(REG_Fcf1,freq_t,1)
            if(back == ITLA_NOERROR):
                back = self.communicate(REG_Fcf2,freq_g,1)  #write the new wavelength to the REG_Fcf2 register
            time_diff = time.time() - init_time
            print(time_diff)
            return back
        if jump == 1:   #if the laser is currently on, use a different register
            back = self.communicate(REG_CjumpTHz,freq_t,1)
            if(back == ITLA_NOERROR):
                back = self.communicate(REG_CjumpGHz,freq_g,1)  #write the new wavelength to the REG_CjumpGHz register
            if(back == ITLA_NOERROR):
                back == self.communicate(REG_Cjumpon,1,1)
            time_diff = time.time() - init_time
            print(time_diff)
            return back
    
    """
    Send a message to the laser to set up the communication link
    """
    def start(self):
        back = self.communicate(REG_Resena,8,1) #start communication by sending 8 to REG_Resena register
        for x in range(10):
            back = self.communicate(REG_Nop,0,0)    #send 0 to REG_Nop register to wait for a "ready" response
        return back
    
    """
    Send the stop message to the laser
    """
    def stop(self):
        back = self.communicate(REG_Resena,0,1) #stop communication by sending 0 to REG_Resena register
        return back

    """
    Function used to send and recieve response messages
    """
    def communicate(self,register,data,rw):
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
            msg[0] = msg[0] | int(self.checksum(msg))*16    #calculate checksum
            self.send(msg)  #send the message
            recvmsg = self.recieve()    #recieve the response from the laser
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
            msg[0] = msg[0] | int(self.checksum(msg))*16    #construct message and send
            self.send(msg)
            recvmsg = self.recieve()    #recieve message
            print("recieved")
            lock.acquire()
            self.queue.pop(0)
            lock.release()
            errorMsg = int(recvmsg[0] & 0x03)
            return(errorMsg)

    """
    Function sends message of four bytes to the laser.
    """
    def send(self,msg):
        self.lasercom.flush()
        print(f"Sent msg: {msg}")
        sendBytes = array.array('B',msg).tobytes()  #construct the bytes from the inputed message
        self.lasercom.write(sendBytes)  #write the bytes on the serial connection

    """
    Functions recieves the next four bytes from the laser.
    """
    def recieve(self):
        reftime = time.time()
        while self.lasercom.inWaiting()<4:  #wait until 4 bytes are recieved
            if(time.time() > reftime + 0.25):   #if it takes longer than 0.25 seconds break
                self._error=ITLA_NRERROR
                return(0xFF,0xFF,0xFF,0xFF)
            time.sleep(0.0001)
        try:
            #num = self.lasercom.inWaiting() #get number of bytes for debugging purposes
            #print(num)
            msg = []
            bAll = self.lasercom.read(num)  #read the four bytes from serial
            print(bAll)
            for b in bAll:
                msg.append(b)   #construct array of bytes from the message
            msg = msg[0:4]
        except:
            print(f"problem with serial communication. queue[0] = {self.queue[0]}")
            msg = [0xFF,0xFF,0xFF,0xFF]
        print(f"Recieved msg: {msg}")
        if self.checksum(msg) == msg[0] >> 4:   #insure the checksum is correct
            print("good cs")
            self._error = msg[0] & 0x03
            return(msg) #return the message recieved
        else:
            print("bad cs")     #if the checksum is wrong, log a CS error
            self._error=ITLA_CSERROR
            return(msg)  

    """
    Function calculates the checksum.
    """
    def checksum(self,msg):     #calculate checksum
        bip8=(msg[0] & 0x0f) ^ msg[1] ^ msg[2] ^ msg[3]
        bip4=((bip8 & 0xf0) >> 4) ^ (bip8 & 0x0f)
        return bip4

    """
    Convert from wavelength to frequency
    """
    def wl_freq(self,unit):
        return C_SPEED/unit

    """
    Lock and unlock serial.
    """
    def SerialLock(self):
        seriallock=1
    
    def SerialUnlock(self):
        seriallock=0
        self.queue.pop(0)    