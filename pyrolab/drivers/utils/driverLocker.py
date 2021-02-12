import os
from os import path

class LOCKER():

    fileName = ""
    status = True

    def __init__(deviceName):
        self.fileName = deviceName + "_LOCK.txt"
    def lock():
        f = open(self.fileName,"w+")
        f.close()
    def release():
        os.remove(self.fileName)
    def bool get_status():
        self.status = os.path.exists(self.fileName)
        return status
        
