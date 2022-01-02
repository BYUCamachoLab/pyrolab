.. _Recommended Libraries:

Recommended Libraries
=====================

Below is a listing of libraries commonly needed by PyroLab, with installation
tips and instructions.


.. _Thorlabs Kinesis Package:

thorlabs_kinesis
----------------

Many of PyroLab's drivers depend on wrappers of ThorLab's Kinesis DLL's 
(Windows only). Python wrappers for these DLL's are available in the
`thorlabs_kinesis <https://github.com/BYUCamachoLab/thorlabs-kinesis>`_ 
package.

The ``thorlabs_kinesis`` package is a wrapper for DLL's provided by ThorLabs
Kinesis Software, available for `free download from their website 
<https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=10285>`_. After 
installing their software, install ``thorlabs_kinesis`` into your Python
environment of choice. 

Configure ``thorlabs_kinesis`` to be able to locate the DLL's on import
(avoids having to insert directories to PATH before importing).
