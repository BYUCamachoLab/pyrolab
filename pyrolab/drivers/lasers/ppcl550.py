# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Pure Photonics Tunable Laser 550 (PPCL550)
-----------------------------------------------
Driver for the Santec PPCL-550 Tunable Laser.
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
class PPCL550:

    latestregister = 0
    tempport = 0
    raybin = 0
    queue = []
    maxrowticket = 0
    lasercom = serial.Serial()

    _error=ITLA_NOERROR
    seriallock = 0
    
    def __init__(self):
        pass

    def connect(self,port,baudrate=9600):
        reftime = time.time()
        connected=False
        try:
            self.lasercom = serial.Serial(port,baudrate,timeout=1,parity=serial.PARITY_NONE)
            #self.communicate(REG_Resena,0,1)
            #self.communicate(REG_Iocap,0,1)
        except serial.SerialException:
            return(ITLA_ERROR_SERPORT)
        baudrate2=4800
        while baudrate2<115200:
            back = self.communicate(REG_Nop,0,0)
            if back != ITLA_NOERROR:
                #go to next baudrate
                if baudrate2==4800: baudrate2=9600
                elif baudrate2==9600: baudrate2=19200
                elif baudrate2==19200: baudrate2=38400
                elif baudrate2==38400: baudrate2=57600
                elif baudrate2==57600: baudrate2=115200
                self.lasercom.close()
                self.lasercom = serial.Serial(port,baudrate2 , timeout=None)            
            else:
                return(ITLA_NOERROR)
        print(baudrate2)
        self.lasercom.close()
        return(ITLA_ERROR_SERBAUD)

    def disconnect(self):
        self.lasercom.close()
        return 0

    def setPower(self,power):
        sendPower = int(power*100)
        back = self.communicate(REG_Power,sendPower,1)
        return back

    def setChannel(self,channel=1):
        back = self.communicate(REG_Channel,channel,1)
        return back

    def setWavelength(self,wavelength):
        if(wavelength < 1570 or wavelength > 1625):
            return "wavelength not in range"
        else:
            freq = self.wl_freq(wavelength)
            freq_t = int(freq/1000)
            freq_g = int(freq*10) - freq_t*10000
            print(freq_t)
            print(freq_g)
            back = self.communicate(REG_Fcf1,freq_t,1)
            if(back == ITLA_NOERROR):
                back = self.communicate(REG_Fcf2,freq_g,1)
            return back
    
    def start(self):
        back = self.communicate(REG_Resena,8,1)
        for x in range(10):
            back = self.communicate(REG_Nop,0,0)
        return back
    
    def stop(self):
        back = self.communicate(REG_Resena,0,1)
        return back

    def communicate(self,register,data,rw):
        lock = threading.Lock()
        lock.acquire()
        rowticket = self.maxrowticket + 1
        self.maxrowticket = self.maxrowticket + 1
        self.queue.append(rowticket)
        lock.release()
        while self.queue[0] != rowticket:
            rowticket=rowticket
        if rw == 0:
            byte2 = int(data/256)
            byte3 = int(data - byte2*256)
            self.latestregister = register
            msg = [rw,register,byte2,byte3]
            msg[0] = msg[0] | int(self.checksum(msg))*16
            self.send(msg)
            recvmsg = self.recieve()
            #print(recvmsg)
            datamsg = recvmsg[2]*256 + recvmsg[3]
            if (recvmsg[0] & 0x03) == 0x02:
                extmsg = self.AEA(datamsg)
                lock.acquire()
                self.queue.pop(0)
                lock.release()
                return extmsg
            lock.acquire()
            self.queue.pop(0)
            lock.release()
            errorMsg = int(recvmsg[0] & 0x03)
            return(errorMsg)
        else:
            byte2=int(data/256)
            byte3=int(data - byte2*256)
            msg = [rw,register,byte2,byte3]
            msg[0] = msg[0] | int(self.checksum(msg))*16
            self.send(msg)
            recvmsg = self.recieve()
            print("recieved")
            lock.acquire()
            self.queue.pop(0)
            lock.release()
            errorMsg = int(recvmsg[0] & 0x03)
            return(errorMsg)

    def send(self,msg):
        self.lasercom.flush()
        print(f"Sent msg: {msg}")
        sendBytes = array.array('B',msg).tobytes()
        self.lasercom.write(sendBytes)

    def recieve(self):
        reftime = time.time()
        while self.lasercom.inWaiting()<4:
            if(time.time() > reftime + 0.25):
                self._error=ITLA_NRERROR
                return(0xFF,0xFF,0xFF,0xFF)
            time.sleep(0.0001)
        try:
            num = self.lasercom.inWaiting()
            print(num)
            msg = []
            bAll = self.lasercom.read(num)
            print(bAll)
            for b in bAll:
                msg.append(b)
            msg = msg[0:4]
        except:
            print(f"problem with serial communication. queue[0] = {self.queue[0]}")
            msg = [0xFF,0xFF,0xFF,0xFF]
        print(f"Recieved msg: {msg}")
        if self.checksum(msg) == msg[0] >> 4:
            print("good cs")
            self._error = msg[0] & 0x03
            return(msg)
        else:
            print("bad cs")
            self._error=ITLA_CSERROR
            return(msg)  

    def checksum(self,msg):
        bip8=(msg[0] & 0x0f) ^ msg[1] ^ msg[2] ^ msg[3]
        bip4=((bip8 & 0xf0) >> 4) ^ (bip8 & 0x0f)
        return bip4

    def wl_freq(self,unit):
        return C_SPEED/unit

    def SerialLock(self):
        seriallock=1
    
    def SerialUnlock(self):
        seriallock=0
        self.queue.pop(0)    