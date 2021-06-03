# Example of how to use the linear stage (Z825B) with software limits locally

# import the Kinesis Library and make sure the path is correct
import os
os.add_dll_directory("C:\\Program Files\\Thorlabs\\Kinesis")

from pyrolab.drivers.motion.z825b import Z825B
# Look at the connected KCube for correct serial num
linear = Z825B("27504851", home=True)

# The stage defaults to the "disallow" limit mode
# and defaults to software limits of 0 and 25 mm 

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

# We will now test the limit mode "disallow"
# it should error if we try to move it outside the limits set
print(f"Before Move: {linear.get_position()} mm")
linear.move_to(5) # Within the limits so no error
print(f"Moved to 5: {linear.get_position()} mm")
try:
    linear.move_to(15) # outside the limits so we must catch the error
except RuntimeError:
    pass
print(f"Should have dissalowed move: {linear.get_position()} mm")

# We will now test the limit mode "partial"
linear.soft_limits_mode = "partial"
linear.move_to(15) # It will move but only until it has reached it's limit
print(f"Should have truncated move to {linear.max_pos}: {linear.get_position()} mm")

# We will now test the limit mode "all"
linear.soft_limits_mode = "all"
linear.move_to(15) # It will simply ignore any software limit set
print(f"Should have ignored max pos at {linear.max_pos}: {linear.get_position()} mm")
linear.move_to(0)

# min and max pos will reset to 0 and 25 mm and soft_limits_mode resets to "disallow"
linear.close()
