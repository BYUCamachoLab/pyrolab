import os
os.add_dll_directory("C:\\Program Files\\Thorlabs\\Kinesis")
from pyrolab.drivers.motion.nanomax300 import NanoMax300

SER_NUM = 71874833

print(f"connecting to {SER_NUM}...")
nm = NanoMax300(str(SER_NUM), closed_loop=True)
print("connected")
print("zeroing all channels...")
nm.zero()
print("zeroed")
x, y, z, = nm.get_position()
print(f"position of x: {x}")
print(f"position of y: {y}")
print(f"position of z: {z}")
while(True):
    channel = int(input("Input channel:"))
    distance = float(input("Input jog distance:"))
    nm.jog(channel,distance)
    cond = input("Break?")
    if(cond == "y" | cond == "yes"):
        break

nm.close()
