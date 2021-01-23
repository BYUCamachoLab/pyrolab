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

from Pyro5.api import expose

import pyrolab.api

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

    latestregister=0
    tempport=0
    raybin=0
    queue=[]
    maxrowticket=0

    _error=ITLA_NOERROR
    seriallock = 0

    def connect(port,baudrate=9600):
        reftime=time.clock()
        connected=False
        try:
            conn = serial.Serial(port,baudrate,timeout=1)
        except serial.SerialException:
            _error = ITLA_ERROR_SERPORT
            return(ITLA_ERROR_SERPORT)
        baudrate2=4800
        while baudrate2<115200:
            self.send(conn,REG_Nop,0,0)
            if ITLALastError() != ITLA_NOERROR:
                #go to next baudrate
                if baudrate2==4800:baudrate2=9600
                elif baudrate2==9600: baudrate2=19200
                elif baudrate2==19200: baudrate2=38400
                elif baudrate2==38400:baudrate2=57600
                elif baudrate2==57600:baudrate2=115200
                conn.close()
                conn = serial.Serial(port,baudrate2,timeout=1)            
            else:
                return(conn)
        conn.close()
        _error = ITLA_ERROR_SERBAUD
        return(ITLA_ERROR_SERBAUD)

    def communicate(sercon,register,data,rw):
        lock = threading.Lock()
        lock.acquire()
        rowticket = self.maxrowticket + 1
        maxrowticket = maxrowticket + 1
        self.queue.append(rowticket)
        lock.release()
        while queue[0] != rowticket:
            rowticket=rowticket
        if rw == 0:
            byte2 = int(data/256)
            byte3 = int(data - byte2*256)
            self.latestregister = register
            msg = [0,register,byte2,byte3]
            msg[0] = msg[0] & checksum(msg)
            self.send(sercon,msg)
            recvmsg = self.recieve(sercon)
            datamsg = recvmsg[2]*256 + recvmsg[3]
            if (recvmsg[0] & 0x03) == 0x02:
                extmsg = self.AEA(sercon,datamsg)
                lock.acquire()
                queue.pop(0)
                lock.release()
                return extmsg
            lock.acquire()
            queue.pop(0)
            lock.release()
            return datamsg
        else:
            byte2=int(data/256)
            byte3=int(data - byte2*256)
            msg = [0,register,byte2,byte3]
            msg[0] = msg[0] & checksum(msg)
            self.send(sercon,msg)
            recvmsg = self.recieve(sercon)
            lock.acquire()
            queue.pop(0)
            lock.release()
            datamsg = recvmsg[2]*256 + recvmsg[3]
            return(datamsg)

    def checksum(msg):
        bip8=(msg[0] & 0x0f) ^ msg[1] ^ msg[2] ^ msg[3]
        bip4=((bip8 & 0xf0) >> 4) ^ (bip8 & 0x0f)
        return bip4

    def SerialLock():
        seriallock=1
    
    def SerialUnlock():
        seriallock=0
        queue.pop(0)

    def __init__(self):
        pass

    