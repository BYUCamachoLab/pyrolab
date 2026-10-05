# Example of how to use the linear stage (Z825B) with software limits locally

# thorlabs_kinesis finds the Kinesis DLLs in C:\Program Files\Thorlabs\Kinesis
# on its own; set THORLABS_DLL_PATHS if they are installed somewhere else.
from pyrolab.drivers.motion.z8xx import Z825B

# Look at the connected KCube for correct serial num
linear = Z825B()
linear.connect(serialno="27504851", home=True)

# connect() puts the stage in the "partial" limit mode, and the limits are
# whatever is saved on the device (0 and 25 mm for the Z825B)

try:
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
    linear.move_to(5)  # Within the limits so no error
    print(f"Moved to 5: {linear.get_position()} mm")
    try:
        linear.move_to(15)  # outside the limits so we must catch the error
    except RuntimeError:
        pass
    print(f"Should have dissalowed move: {linear.get_position()} mm")

    # We will now test the limit mode "partial"
    linear.soft_limits_mode = "partial"
    linear.move_to(15)  # It will move but only until it has reached it's limit
    print(f"Should have truncated move to {linear.max_pos}: {linear.get_position()} mm")

    # We will now test the limit mode "all"
    linear.soft_limits_mode = "all"
    linear.move_to(15)  # It will simply ignore any software limit set
    print(
        f"Should have ignored max pos at {linear.max_pos}: {linear.get_position()} mm"
    )
    linear.move_to(0)
finally:
    # the next connect() reloads the limits saved on the device and goes back
    # to the "partial" limit mode
    linear.close()
