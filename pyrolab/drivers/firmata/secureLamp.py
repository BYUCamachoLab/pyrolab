import lamp
import os
from os import path

class SECURE_LAMP(ARD_LAMP):

    def __init__():
        status = self.get_status()
        if(status == "unlocked"):
            super.__init__()
    def lock():
        f = open("LOCK_LAMP.txt","w+")
        f.close()
    def release():
        os.remove("LOCK_LAMP.txt")
    def get_status():
        x = os.path.exists("LOCK_LAMP.txt")
        print(x)
