import pyrolab.drivers.firmata.lamp as lamp
import os
from os import path
from Pyro5.api import expose
import pyrolab.api

@expose
class SECURE_LAMP(lamp.LAMP):

    def __init__(self,port):
        status = self.get_status()
        if(status == "unlocked"):
            super.__init__(port)
    def lock(self):
        f = open("LOCK_LAMP.txt","w+")
        f.close()
    def release(self):
        os.remove("LOCK_LAMP.txt")
    def get_status(self):
        x = os.path.exists("LOCK_LAMP.txt")
        print(x)
