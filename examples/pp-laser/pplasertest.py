from pyrolab.api import locate_ns, Proxy
import cv2
import sys
import time

ns = locate_ns(host="camacholab.ee.byu.edu")
laser = Proxy(ns.lookup("PPCL550"))

back = laser.connect("COM4",baudrate=9600)
print(back)
back = laser.setPower(10)
print(back)
back = laser.setWavelength(1590)
print(back)
back = laser.setChannel(1)
print(back)
back = laser.start()
print(back)
time.sleep(10)
back = laser.stop()
print(back)
back = laser.disconnect()
print(back)