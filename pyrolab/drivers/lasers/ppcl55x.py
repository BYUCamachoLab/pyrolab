# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Pure Photonics Tunable Laser
============================

Driver for Pure Photonic tunable lasers.

.. note::

   Pure Photonic offers GUI controllers, a command line interface, and 
   DLL/driver downloads on their 
   `website <https://www.pure-photonics.com/downloads1>`_. These are not
   required by PyroLab, however.

.. admonition:: Dependencies
   :class: note

   pyserial
"""

import array
import logging
import threading
import time
from typing import List

import serial
import numpy as np
from Pyro5.api import expose
from scipy.constants import speed_of_light as C_SPEED

log = logging.getLogger(__name__)

from pyrolab.drivers.lasers import Laser
from pyrolab.errors import CommunicationError

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
REG_Lfo1=0x40
REG_Lfo2=0x41
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

WRITE_ONLY=0
WRITE_READ=1


@expose
class PPCL55xBase(Laser):
    """
    Base class for a generic Pure Photonics Tunable Laser. Do not instantiate.

    The laser must already be physically powered and connected to a USB port
    of some host computer, whether that be a local machine or one hosted by 
    a PyroLab server. Methods such as :py:func:`on` and :py:func:`off` will 
    simply turn the laser diode on and off, not the laser itself.
    """
    # Attributes
    # ----------
    # MINIMUM_WAVELENGTH : float
    #     The minimum wavelength of the laser in nanometers (value 1500).
    # MAXIMUM_WAVELENGTH : float
    #     The maximum wavelength of the laser in nanometers (value 1600).
    # MINIMUM_POWER_DBM : float
    #     The minimum power of the laser in dBm (value 7).
    # MAXIMUM_POWER_DBM : float
    #     The maximum power of the laser in dBm (value 13.5).

    MINIMUM_WAVELENGTH = 1500
    MAXIMUM_WAVELENGTH = 1600
    MINIMUM_POWER_DBM = 7
    MAXIMUM_POWER_DBM = 13.5

    MINIMUM_FREQUENCY = C_SPEED / MAXIMUM_WAVELENGTH
    MAXIMUM_FREQUENCY = C_SPEED / MINIMUM_WAVELENGTH
    MINIMUM_POWER_MW = 10**(MINIMUM_POWER_DBM/10)
    MAXIMUM_POWER_MW = 10**(MAXIMUM_POWER_DBM/10)

    def connect(self, port: str="", baudrate: int=9600) -> None:
        """
        Connects to and initializes the laser. All parameters are keyword arguments.

        Parameters
        ----------
        port : str
            COM port the laser is connected to (default "")
        baudrate : int
            baudrate of the serial connection (default 9600)
        """

        self.latest_register = 0
        self.queue = []
        self.laser_on = False
        self.max_row_ticket = 0

        try:
            self.device = serial.Serial(port,baudrate,timeout=1,
                parity=serial.PARITY_NONE) #attempt connection with given baudrate
        except serial.SerialException as e:
            self.device.close()
            raise CommunicationError("Could not connect to laser on port " + port
            + " with baudrate " + str(baudrate))
            raise e

    def close(self) -> None:
        """
        Disconnect from the laser
        """

        self.device.close()
    
    def power_mW(self,power: float=None) -> float:
        """
        Set the power on the laser.

        Parameters
        ----------
        power : float
            Power that the laser will be set to in mW

        Returns
        -------
        int
            Integer representing error message, 0 if no error.
        """
        if power is not None:
            if(power < self.MINIMUM_POWER_MW or power > self.MAXIMUM_POWER_MW):
                raise ValueError("Inputed power not in acceptable range "
                + str(self.MINIMUM_POWER_MW) + " to " + str(self.MAXIMUM_POWER_MW))

            sendPower = int(np.log10(power) * 1000)  #scale the power inputed
            #on the REG_Power register, send the power
            self._communicate(REG_Power,sendPower,1)
        else:
            message = self._communicate(REG_Oop,0,0)
            power = np.round(np.power(10.0,(256.0*message[2] + message[3])/1000.0)*100.0)/100.0
            if power > self.MAXIMUM_POWER_MW*1.1:
                power = 0
            return power



    def power_dBm(self,power: float=None) -> float:
        """
        Set the power on the laser.

        Parameters
        ----------
        power : float
            Power that the laser will be set to in dBm
        
        Returns
        -------
        int
            Integer representing error message, 0 if no error.
        """
        if power is not None:
            if(power < self.MINIMUM_POWER_DBM or power > self.MAXIMUM_POWER_DBM):
                raise ValueError("Inputed power not in acceptable range "
                + str(self.MINIMUM_POWER_DBM) + " to " + str(self.MAXIMUM_POWER_DBM))
            sendPower = int(power*100)  #scale the power inputed
            #on the REG_Power register, send the power
            self._communicate(REG_Power,sendPower,1)
        else:
            message = self._communicate(REG_Oop,0,0)
            power = (256.0*message[2] + message[3])/100.0
            if power > self.MAXIMUM_POWER_DBM*1.1:
                power = 0
            return power

    def set_channel(self,channel: int) -> int:
        """
        Set the channel (should always be 1)

        Parameters
        ----------
        channel : int
            channel that the laser is on
        
        Returns
        -------
        int
            Integer representing error message, 0 if no error.
        """
        #on the REG_Channel register, send the channel
        response = self._communicate(REG_Channel,channel,1)  
        return response
    
    def set_mode(self,mode: int) -> int:
        """
        Set the mode of operation for the laser

        Parameters
        ----------
        mode : int
            | The mode corresponds to the following modes of the laser:
            | 0: Regular mode
            | 1: No dither mode
            | 2: Clean mode
        
        Returns
        -------
        int
            Integer representing error message, 0 if no error.
        """
        #on the REG_Mode register, send the mode
        response = self._communicate(REG_Mode,mode,1)
        return response
    
    def frequency(self,frequency: float=None) -> float:
        """
        Set the frequncy of the laser.
        
        .. important::
            Laser must be off in order to set the frequency. Therefore, if the 
            laser is not off this function will turn it off, set the frequency,
            then turn it back on.

        Parameters
        ----------
        frequency : float
            Frequency of the laser to be set in THz
        
        Returns
        -------
        int
            Integer representing error message, 0 if no error.
        """
        if frequency is not None:
            #if the wavelength is not in the allowed range
            if(frequency < self.MINIMUM_FREQUENCY or frequency > self.MAXIMUM_FREQUENCY):
                raise ValueError("Inputed frequency not in acceptable range "
                + str(self.MINIMUM_FREQUENCY) + " to " + str(self.MAXIMUM_FREQUENCY))
            
            frequency = np.round(frequency*10.0)/10.0
            freq_t = int(frequency/1000)
            #convert the wavelength to frequency for each register
            freq_g = int(frequency*10) - freq_t*10000    

            if self.power_dBm() > 0:   #if the laser is currently on
                self.off()
                self._communicate(REG_Fcf1,freq_t,1)
                self._communicate(REG_Fcf2,freq_g,1)
                while self.frequency() != frequency:
                    time.sleep(0.01)
                self.on()
            else:
                self._communicate(REG_Fcf1,freq_t,1)
                self._communicate(REG_Fcf2,freq_g,1)
        else:
            t_message = self._communicate(REG_Lfo1,0,0)
            g_message = self._communicate(REG_Lfo2,0,0)
            freq_t = 256.0*t_message[2] + t_message[3]
            freq_g = 256.0*g_message[2] + g_message[3]
            frequency = freq_t*1000.0 + freq_g/10.0
            return frequency


    def wavelength(self,wavelength: float=None) -> float:
        """
        Set the wavelength of the laser.
        
        .. important::
            Laser must be off in order to set the wavelength. Therefore, if the 
            laser is not off this function will turn it off, set the wavelength,
            then turn it back on.

        Parameters
        ----------
        wavelength : float
            Wavelength of the laser to be set in nm
        
        Returns
        -------
        int
            Integer representing error message, 0 if no error.
        """
        
        if wavelength is not None:
            #if the wavelength is not in the allowed range
            if(wavelength < self.MINIMUM_WAVELENGTH or wavelength > self.MAXIMUM_WAVELENGTH):
                raise ValueError("Inputed wavelength not in acceptable range "
                + str(self.MINIMUM_WAVELENGTH) + " to " + str(self.MAXIMUM_WAVELENGTH))
            
            frequency = np.round(C_SPEED/wavelength*10.0)/10.0
            freq_t = int(frequency/1000)
            #convert the wavelength to frequency for each register
            freq_g = int(frequency*10) - freq_t*10000    

            if self.power_dBm() > 0:   #if the laser is currently on
                self.off()
                self._communicate(REG_Fcf1,freq_t,1)
                self._communicate(REG_Fcf2,freq_g,1)
                while self.frequency() != frequency:
                    time.sleep(0.01)
                self.on()
            else:
                self._communicate(REG_Fcf1,freq_t,1)
                self._communicate(REG_Fcf2,freq_g,1)
        else:
            t_message = self._communicate(REG_Lfo1,0,0)
            g_message = self._communicate(REG_Lfo2,0,0)
            freq_t = 256.0*t_message[2] + t_message[3]
            freq_g = 256.0*g_message[2] + g_message[3]
            frequency = freq_t*1000.0 + freq_g/10.0
            wavelength = np.round(C_SPEED/frequency*1000.0)/1000.0
            return wavelength

    def on(self) -> int:
        """
        Turn on the laser

        Returns
        -------
        int
            Integer representing error message, 0 if no error.
        """
        #start communication by sending 8 to REG_Resena register
        response = self._communicate(REG_Resena,8,1)
        for i in range(10):
            #send 0 to REG_Nop to allow time for laser diode to turn on
            response = self._communicate(REG_Nop,0,0)
        self.is_on = True
        return response

    def off(self) -> int:
        """
        Turn off the laser

        Returns
        -------
        int
            Integer representing error message, 0 if no error.
        """
        #stop communication by sending 0 to REG_Resena register
        response = self._communicate(REG_Resena,0,1)
        for i in range(10):
            #send 0 to REG_Nop to allow time for laser diode to turn on
            response = self._communicate(REG_Nop,0,0)
        self.is_on = False
        return response

    def _communicate(self,register: int,data: int,write_read: int) -> int:
        """
        Function that implements the commmunication with the laser. It will 
        first send a message then receive a response if wanted.

        Parameters
        ----------
        register : int
            Register to which will be written to on the laser
        data : int
            User-specific data that will be sent to the laser
        write_read : int
            | Defines if the communication is only write or write-read
            | 0: Write only
            | 1: Write then read

        Returns
        -------
        int
            Integer representing error message, 0 if no error.
        """

        lock = threading.Lock()
        lock.acquire()
        row_ticket = self.max_row_ticket + 1
        self.max_row_ticket = self.max_row_ticket + 1
        self.queue.append(row_ticket)
        lock.release()
        while self.queue[0] != row_ticket:
            row_ticket=row_ticket
        data_byte_0 = int(data/256)
        data_byte_1 = int(data - data_byte_0*256)
        self.latest_register = register      #modify bytes for sending
        message = [write_read,register,data_byte_0,data_byte_1]
        self._send(message)  #send the message
        received_message = self._receive()    #receive the response from the laser
        lock.acquire()
        self.queue.pop(0)
        lock.release()
        # error_message = int(received_message[0] & 0x03)
        return(received_message)

    """
    Function sends message of four bytes to the laser.
    """
    def _send(self,message: List[int]) -> None:
        """
        Sends message of four bytes to the laser after calculating the checksum

        Parameters
        ----------
        message : List[int]
            Message that will be sent to the laser
        """
        message[0] = message[0] | int(self._checksum(message))*16    #calculate checksum
        log.debug(f"sending message: {message}")
        self.device.flush()
        #construct the bytes from the inputed message
        send_bytes = array.array('B',message).tobytes()  
        self.device.write(send_bytes)  #write the bytes on the serial connection

    def _receive(self) -> List[int]:
        """
        Receives and verifies message from the laser with checksum
        
        Returns
        -------
        List[int]
            Bytes of message received.

        Raises
        ------
        PyroLabException.CommunicationException
        """

        reference_time = time.time()
        while self.device.inWaiting()<4:  #wait until 4 bytes are received
            if(time.time() > reference_time + 0.5): #if it takes longer than 0.5 seconds break
                return(0xFF,0xFF,0xFF,0xFF)
        try:
            num = self.device.inWaiting() #get number of bytes for debugging purposes
            message = []
            bytes_read = self.device.read(num)  #read the four bytes from serial
            for b in bytes_read:
                message.append(b)   #construct array of bytes from the message
            message = message[0:4]
        except:
            raise CommunicationError("No response from laser")
        if self._checksum(message) == message[0] >> 4: # ensure the checksum is correct
            log.debug(f"message received: {message[2]} {message[3]}")
            return(message) #return the message received
        else:
            #if the checksum is wrong, log a CS error
            raise CommunicationError("Incorrect checksum returned")

    def _checksum(self,message: List[int]) -> int:     #calculate checksum
        """
        Calculate the checksum of a message

        Parameters
        ----------
        message : List[int]
            Four-byte message that will be used to produce a checksum
        
        Returns
        -------
        int
            Calculated checksum
        """

        bip_8=(message[0] & 0x0f) ^ message[1] ^ message[2] ^ message[3]
        bip_4=((bip_8 & 0xf0) >> 4) ^ (bip_8 & 0x0f)
        return bip_4


@expose
class PPCL550(PPCL55xBase):
    """
    Driver for a Pure Photonic PPCL550 series laser.

    The laser must already be physically powered and connected to a USB port
    of some host computer, whether that be a local machine or one hosted by 
    a PyroLab server. Methods such as :py:func:`on` and :py:func:`off` will 
    simply turn the laser diode on and off, not the laser itself.

    Attributes
    ----------
    MINIMUM_WAVELENGTH : float
        The minimum wavelength of the laser in nanometers (value 1529).
    MAXIMUM_WAVELENGTH : float
        The maximum wavelength of the laser in nanometers (value 1566).
    MINIMUM_POWER_DBM : float
        The minimum power of the laser in dBm (value 7).
    MAXIMUM_POWER_DBM : float
        The maximum power of the laser in dBm (value 13.5).
    """

    MINIMUM_WAVELENGTH = 1529
    MAXIMUM_WAVELENGTH = 1566
    MINIMUM_POWER_DBM = 7
    MAXIMUM_POWER_DBM = 13.5


@expose
class PPCL551(PPCL55xBase):
    """
    Driver for a Pure Photonic PPCL551 series laser.

    The laser must already be physically powered and connected to a USB port
    of some host computer, whether that be a local machine or one hosted by 
    a PyroLab server. Methods such as :py:func:`on` and :py:func:`off` will 
    simply turn the laser diode on and off, not the laser itself.

    Attributes
    ----------
    MINIMUM_WAVELENGTH : float
        The minimum wavelength of the laser in nanometers (value 1572).
    MAXIMUM_WAVELENGTH : float
        The maximum wavelength of the laser in nanometers (value 1609).
    MINIMUM_POWER_DBM : float
        The minimum power of the laser in dBm (value 7).
    MAXIMUM_POWER_DBM : float
        The maximum power of the laser in dBm (value 13.5).
    """

    MINIMUM_WAVELENGTH = 1572
    MAXIMUM_WAVELENGTH = 1609
    MINIMUM_POWER_DBM = 7
    MAXIMUM_POWER_DBM = 13.5
