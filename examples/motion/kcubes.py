import os
os.add_dll_directory("C:\\Program Files\\Thorlabs\\Kinesis")

from ctypes import c_int, c_double, byref, pointer
import time

from pyrolab.drivers.motion.z825b import Z825B
linear = Z825B("27003497", home=False)
while True:
    rot_pos = int(input("Translation Position:"))
    pos = linear.get_position()
    print(f"Before Move: {pos}")
    linear.move_to(rot_pos)
    pos = linear.get_position()
    print(f"After Move: {pos}")

linear.close()
