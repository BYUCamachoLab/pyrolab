# PyroLab
A framework for using remote lab instruments as local resources, built on Pyro5.

Developed by Sequoia Ploeg (for [CamachoLab](https://camacholab.byu.edu/), 
Brigham Young University).

## About
This project aims to allow all laboratory instruments to be accessed as
local objects from a remote machine. Instruments that don't natively
support such access, such as those required to be connected by a USB cable
(or similar), are wrapped with a Pyro5 interface. However, this library may
contain other instruments that are already internet-capable and don't rely
on Pyro5. That's alright; we're just trying to create a minimal-dependency,
one-stop-shop for laboratory instruments!

## FAQ's
1. **Another instrument library? What about all the others?**  
    In our experience, etc.

2. **Is this a standalone software that automatically supports all the advertised 
instruments?**  
    No; many of these instruments depend on other software already being
    installed. In particular, ThorLabs equipment depends on ThorLabs software
    already being installed on the computer connected to the physical hardware
    (but not on the remote computer!).

## For Developers
Since the passing of data is, by definition, between hosts and over IP, PyroLab
avoids the use of complex Python objects for return values that will be 
transmitted to remote machines. Since serialization is complicated, and
security is even harder, we resort to using only basic Python types when
interfacing with hardware (i.e., Python lists, ints, tuples, and not NumPy 
arrays, matplotlib plot objects, custom objects, etc.).
