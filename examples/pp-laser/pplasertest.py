from pyrolab.api import locate_ns, Proxy
import cv2
import sys
import time

ns = locate_ns(host="camacholab.ee.byu.edu")
laser = Proxy(ns.lookup("PPCL550"))

back = laser.start("COM6",baudrate=9600)
print(back)
back = laser.setPower(13.5)
print(back)
back = laser.setWavelength(1550)
print(back)
back = laser.setChannel(1)
print(back)
back = laser.on()
print(back)
time.sleep(10)
back = laser.setPower(5)
print(back)
time.sleep(10)
back = laser.off()
print(back)
back = laser.close()
print(back)