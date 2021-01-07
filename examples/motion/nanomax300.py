import os
os.add_dll_directory("C:\\Program Files\\Thorlabs\\Kinesis")

from pyrolab.drivers.motion.nanomax300 import NanoMax300
nm = NanoMax300("71874833", closed_loop=True)

nm.zero()
x, y, z, = nm.get_position()
nm.jog(1, 0.1)

nm.close()
