import os
os.add_dll_directory("C:\\Program Files\\Thorlabs\\Kinesis")

from pyrolab.drivers.motion.prm1z8 import PRM1Z8
rotator = PRM1Z8("27003366", home=True)

rotator.close()
