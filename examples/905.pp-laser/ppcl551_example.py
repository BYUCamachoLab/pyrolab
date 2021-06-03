# Example of how to use the Pure Photonics pp551 laser locally

# import the the pyrolab class
from pyrolab.drivers.lasers.ppcl550 import PPCL55x

import time

# The 551 laser has a range of 1569-1625 nm, power range of 6-13.5 dBm
# choose the correct COM port 
laser = PPCL55x(minWL=1569, maxWL=1625, port="COM5")

# set the power wavelength and channel
laser.setPower(13.5)
laser.setWavelength(1570)
laser.setChannel(1)

# turn the laser on
laser.on()
time.sleep(10)

# adjust the power to 10 dBm
print("setting the power to 10 dBm")
laser.setPower(10)
time.sleep(10)

# change the wavelength to 1600 nm
print("setting wavelength to 1600 nm")
laser.setWavelength(1600)
time.sleep(10)
laser.off()
laser.close()