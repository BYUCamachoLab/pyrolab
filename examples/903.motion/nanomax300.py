import os
os.add_dll_directory("C:\\Program Files\\Thorlabs\\Kinesis")
from pyrolab.drivers.motion.max31x import MAX31X
import time

SER_NUM = 71874833

print(f"connecting to {SER_NUM}...")
nm = MAX31X(str(SER_NUM), closed_loop=True)
print("connected")
print("zeroing all channels...")
nm.zero()
print("zeroed")
x, y, z, = nm.get_position()
print(f"position of x: {x}")
print(f"position of y: {y}")
print(f"position of z: {z}")
print("Input Jogging Parameters:")
while(True):
    channel = int(input("Input channel:"))
    distance = float(input("Input jog distance:"))
    print(f"jogging channel {channel} a distance of {distance}...")
    nm.jog(channel,distance)
    time.sleep(1)
    print("jog complete")
    x, y, z, = nm.get_position()
    print(f"new position of x: {x}")
    print(f"new position of y: {y}")
    print(f"new position of z: {z}")
    cond = input("Break?")
    if((cond == "y") | (cond == "yes")):
        break
print("closing nanomax...")
nm.close()
print("closed")
