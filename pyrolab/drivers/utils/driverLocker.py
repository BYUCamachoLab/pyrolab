import os
from os import path
import pyfirmata
import time
from Pyro5.api import expose
import pyrolab.api

@expose
class Locker():

    fileName = ""
    status = True
    MASTER_PWD = "override"

    def __init__(self,deviceName):
        self.fileName = "C:\\LockedDevices\\" + deviceName + "_LOCK.txt"

    def lock(self,pwd=""):
        exists = self.get_status()
        if exists == True:
            return 1
        else:
            self.password = pwd
            f = open(self.fileName,"w")
            f.write(pwd)
            f.close()
            return 1

    def release(self,name=""):
        exists = self.get_status()
        if exists == True:
            f = open(self.fileName,"r")
            pwd = f.read()
            f.close()
            if (name == pwd or name == self.MASTER_PWD):
                os.remove(self.fileName)
                return 1
            else:
                return 0
        else:
            return 1

    def get_status(self):
        self.status = os.path.exists(self.fileName)
        return self.status
    
    def get_user(self):
        exists = self.get_status()
        if exists == True:
            f = open(self.fileName,"r")
            name = f.read()
            f.close()
            return name
        else:
            return ""
        
