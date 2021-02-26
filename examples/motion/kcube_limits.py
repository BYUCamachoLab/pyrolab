import os
os.add_dll_directory("C:\\Program Files\\Thorlabs\\Kinesis")

from ctypes import c_int, c_double, byref, pointer
import time

from pyrolab.drivers.motion.z825b import Z825B
linear = Z825B("27003497", home=True)

# read and set all the different types of software limits modes
print(linear.soft_limits_mode)
linear.soft_limits_mode = "partial"
print(linear.soft_limits_mode)
linear.soft_limits_mode = "all"
print(linear.soft_limits_mode)
linear.soft_limits_mode = "disallow"
print(linear.soft_limits_mode)

# read and set the max position
print(f"max pos: {linear.max_pos} mm")
linear.max_pos = 10
print(f"max pos: {linear.max_pos} mm")


print(f"Before Move: {linear.get_position()} mm")
linear.move_to(5)
print(f"Moved to 5: {linear.get_position()} mm")
try:
    linear.move_to(15)
except RuntimeError:
    pass
print(f"Should have dissalowed move: {linear.get_position()} mm")
linear.soft_limits_mode = "partial"
linear.move_to(15)
print(f"Should have truncated move to {linear.max_pos}: {linear.get_position()} mm")
linear.soft_limits_mode = "all"
linear.move_to(15)
print(f"Should have ignored max pos at {linear.max_pos}: {linear.get_position()} mm")
linear.move_to(0)

# min and max pos will reset to 0 and 25 mm and soft_limits_mode resets to "disallow"
linear.close()
