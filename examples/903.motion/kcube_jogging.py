# Example of how to use the linear stage (Z825B) with software limits locally

# import the Kinesis Library and make sure the path is correct
import os

os.add_dll_directory("C:\\Program Files\\Thorlabs\\Kinesis")

from pyrolab.drivers.motion.z8xx import Z825B

# Look at the connected KCube for correct serial num
linear = Z825B("27504851", home=True)

# Set and read a few of the parameters pertaining to jogging
print(f"Jog mode: {linear.jog_mode}")
print(f"Stop mode: {linear.stop_mode}")
print(f"Jog step size: {linear.jog_step_size}")
linear.jog_step_size = 1
print(f"Jog step size: {linear.jog_step_size}")
linear.max_pos = 15
print(f"jog velocity: {linear.jog_velocity}")
print(f"jog acceleration: {linear.jog_acceleration}")
print(f"Soft Limit mode: {linear.soft_limits_mode}")

# Jog the position twice and measure position after each step
linear.jog("forward")
print(f"current pos after 1 jog: {linear.get_position()} mm")
linear.jog("forward")
print(f"current pos after 2 jogs: {linear.get_position()} mm")

# change to continuous jog then measure the position after reaching 10 mm
linear.jog_mode = "continuous"
linear.jog_velocity = 1
linear.jog("forward")
while linear.get_position() < 10.0:
    pass
linear.stop()
print(f"current pos after continuous jog: {linear.get_position()} mm")
linear.move_to(0)

linear.close()
