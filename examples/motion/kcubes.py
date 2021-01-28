import os
os.add_dll_directory("C:\\Program Files\\Thorlabs\\Kinesis")

from pyrolab.drivers.motion.prm1z8 import PRM1Z8
rotator = PRM1Z8("27003366", home=True)
while True:
    rot_pos = int(input("Rotational Position:"))
    pos = rotator.get_pos()
    print(f"Before Move: {pos}")
    rotator.move_by(rot_pos)
    pos = rotator.get_pos()
    print(f"After Move: {pos}")


rotator.close()
