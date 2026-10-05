# Example of how to use the rotation stage (PRM1Z8) locally

# thorlabs_kinesis finds the Kinesis DLLs in C:\Program Files\Thorlabs\Kinesis
# on its own; set THORLABS_DLL_PATHS if they are installed somewhere else.
from pyrolab.drivers.motion.prm1z8 import PRM1Z8

# Look at the connected KCube for correct serial num
rot = PRM1Z8()
rot.connect(serialno="27003366", home=False)

try:
    # Prints out the starting postition to get an idea of where it currently is
    starting_pos = rot.get_position()
    print(f"Stating position: {starting_pos} degrees")

    # A simple script to test moving the stage
    while True:
        # Input a position in degrees
        move_pos = float(input("Rotation Position (deg):"))
        # Input a 0 to go back to the starting position and exit the program
        if move_pos == 0:
            break
        pos = rot.get_position()
        print(f"Before Move: {pos} degrees")
        rot.move_to(move_pos)
        pos = rot.get_position()
        print(f"After Move: {pos} degrees")
    rot.move_to(starting_pos)
finally:
    rot.close()
