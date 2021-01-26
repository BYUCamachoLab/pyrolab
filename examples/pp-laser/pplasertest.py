from pyrolab.drivers.lasers import ppcl550 as ppl
import time

laser = ppl.PPCL550()
back = laser.connect("COM4",baudrate=115200)
print(back)
back = laser.setPower(14)
print(back)
back = laser.setWavelength(1550)
print(back)
back = laser.setChannel(1)
print(back)
back = laser.start()
print(back)
time.sleep(5)
back = laser.stop()
print(back)
back = laser.disconnect()
print(back)

