import os
os.add_dll_directory("C:\\Program Files\\Thorlabs\\Kinesis")

from ctypes import c_int, c_double, byref, pointer
import time

from pyrolab.drivers.motion.z8xx import Z825B
linear = Z825B("27003497", home=False)
while True:
    move_pos = int(input("Translation Position:"))
    if move_pos == 0:
        break
    pos = linear.get_position()
    print(f"Before Move: {pos}")
    linear.move_to(move_pos)
    pos = linear.get_position()
    print(f"After Move: {pos}")
linear.move_to(0)
linear.close()
