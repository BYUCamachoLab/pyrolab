import os
from os import path
import pyfirmata
import time
from Pyro5.api import expose
import pyrolab.api

@expose
class LOCKER():

    fileName = ""
    status = True
    MASTER_PWD = "override"

    def __init__(self,deviceName):
        self.fileName = deviceName + "_LOCK.txt"

    def lock(self,pwd=""):
        exists = self.get_status()
        if exists == True:
            return "already locked"
        else:
            self.password = pwd
            f = open(self.fileName,"w")
            f.write(pwd)
            f.close()
            return "locked"

    def release(self,pwd=""):
        exists = self.get_status()
        if exists == True:
            f = open(self.fileName,"r")
            password = f.read()
            f.close()
            if (password == pwd or self.MASTER_PWD == pwd):
                os.remove(self.fileName)
                return "released"
            else:
                return "realease is password protected"
        else:
            return "already released"

    def get_status(self):
        self.status = os.path.exists(self.fileName)
        return self.status
        
