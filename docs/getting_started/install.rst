.. _getting_started_install:


Installation
============

The easiest way to install PyroLab is to install it via pip, a cross platform 
Python package installer. This is the recommended installation method for most 
users.

Considerations
--------------

1. **Is this installation serving as a client?** 
   The PyroLab client is designed to be platform agnostic. It should work on
   any OS, regardless of the OS running the server.
2. **Is this installation serving as a server (providing services/instruments)?** 
   You need to make sure that the drivers needed to connect to your devices are
   available on the OS of choice. For example, certain drivers are only 
   available on Windows. Check the documentation for the driver before 
   installing.
3. **Is this installation acting as a nameserver (server phonebook)?** 
   It is recommended you use a Linux installation for the nameserver, due to 
   the simplicity of security, opening ports, and running servers on Linux.
   However, the nameserver is the simplest mechanism in PyroLab, and can run
   easily on any operating system.

Python Version Support
----------------------

PyroLab officially supports Python 3.7 to 3.11.


Installing PyroLab
------------------


A note about dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^

Since PyroLab supports many drivers but may only be configured on specific
computers with a few different devices, it does not install all potential 
dependencies by default.

Some drivers, for example, have dependencies that are OS-specific. And, for
machines that will be acting purely as clients, you do not need the 
dependencies in order to access services running on other machines. Only the
computer hosting a given service needs its dependencies. Be sure to
visit each driver's documentation for a listing of packages you may need to
preinstall.

For drivers or services that have packages installable from PyPI, a pip install
with extras is sufficient (see below). Some drivers may require additional 3rd
party software to be installed (such as ThorLabs' Kinesis DLL's), see the
respetive drivers' documentation.


Installing with pip
^^^^^^^^^^^^^^^^^^^

PyroLab supports many different drivers but aims to avoid clogging up your 
system with all the potential dependencies. Therefore, installation "extras" 
are provided for installing the Python dependencies of each desired feature.

For a basic installation, run:

.. code-block:: bash

   pip install pyrolab

You can install the extras (or multiple of them) using the following command:

.. code-block:: bash

   pip install pyrolab[feature]
   pip install pyrolab[feature1,feature2,feature3]

Available extras:

* ``tsl550`` (Santec TSL-550 Laser)
* ``ppcl55x`` (Pure Photonics Lasers)
* ``rto`` (Rohde-Schwarz Oscilloscopes)
* ``arduino``
* ``monitor`` (The web interface for nameservers) 


Installing from git
^^^^^^^^^^^^^^^^^^^

You can also install directly from git by first cloning the repository. After
cloning, we still recommend using an "editable" pip install to setup all the
paths and register the command line program. That looks like this:

.. code-block:: bash

   git clone https://github.com/BYUCamachoLab/pyrolab
   cd pyrolab
   pip install -e .
   # Or, with some extras:
   pip install -e .[tsl550,ppcl55x,rto,arduino]

If deep down in your soul, you truly hate pip installing and just want to add
things to your PATH to install them, you can add the directory containing
PyroLab to your PATH. Additionally, the command line program can be invoked
by executing:

.. code-block:: bash

   python -m pyrolab.cli


Data Directories
----------------

PyroLab stores a fair amount of installation-specific data on the user's
computer. This includes configuration files that allow you to specify hosted
services or instruments, log files, and other data files. This data is stored
in the same directory as your PyroLab installation (which in turn depends on
how PyroLab was installed). If you wish, you can see where PyroLab stores its
data by running one of the following:

.. code-block:: bash

   # If PyroLab is installed on the command line
   pyrolab --show-data-dir

   # If running from the source directory
   python -m pyrolab.cli --show-data-dir
