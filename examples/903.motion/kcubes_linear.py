# Example of how to use the linear stage (Z825B) locally

# thorlabs_kinesis finds the Kinesis DLLs in C:\Program Files\Thorlabs\Kinesis
# on its own; set THORLABS_DLL_PATHS if they are installed somewhere else.
from pyrolab.drivers.motion.z8xx import Z825B

# Look at the connected KCube for correct serial num
linear = Z825B()
linear.connect(serialno="27504851", home=False)

try:
    # Prints out the starting postition to get an idea of where it currently is
    starting_pos = linear.get_position()
    print(f"Stating position: {starting_pos} mm")

    # A simple script to test moving the stage
    while True:
        # Input a position in mm
        move_pos = float(input("linear Position (mm):"))
        # Input a 0 to go back to the starting position and exit the program
        if move_pos == 0:
            break
        pos = linear.get_position()
        print(f"Before Move: {pos} mm")
        linear.move_to(move_pos)
        pos = linear.get_position()
        print(f"After Move: {pos} mm")
    linear.move_to(starting_pos)
finally:
    linear.close()
