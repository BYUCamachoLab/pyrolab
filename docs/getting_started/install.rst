
Installation
============

The easiest way to install PyroLab is to install it via pip, a cross platform 
Python package installer. This is the recommended installation method for most 
users.

Considerations
--------------

1. Is this installation serving as a client?
   The PyroLab client is designed to be platform agnostic. It should work on
   any OS, regardless of the OS running the server.
2. Is this installation serving as a server?
   You need to make sure that the drivers needed to connect to your devices are
   available on the OS of choice. For example, certain drivers are only 
   available on Windows. Check the documentation for the driver before 
   installing.
3. Is this installation acting as a nameserver?
   It is recommended you use a Linux installation for the nameserver, due to 
   the simplicity of security, opening ports, and running servers on Linux.

Python Version Support
----------------------

PyroLab officially supports Python 3.7 to 3.9.

Installing PyroLab
------------------

Installing with pip
^^^^^^^^^^^^^^^^^^^

PyroLab supports many different drivers but aims to avoid clogging up your 
system with all the potential dependencies. Therefore, options are provided
for installing dependencies for each desired feature.

Installing from git
^^^^^^^^^^^^^^^^^^^

You can also install directly from git by first cloning the repository.

Dependencies
^^^^^^^^^^^^

Since PyroLab supports many drivers but may only be configured on specific
computers with a few different devices, it does not install all dependencies
by default.

Some drivers, for example, have dependencies that are OS-specific. Be sure to
visit each driver's documentation for a listing of packages you should
preinstall.
