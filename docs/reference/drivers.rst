.. _api.drivers:

pyrolab.drivers
===============

.. warning:: 
   
   It is the responsibility of the user to ensure parameters are within the
   physical limits of the hardware. The software may or may not perform checks
   to validate input, but given the nature of a driver potentially working with
   several devices with different valid ranges, and the possibility of drivers
   being contributed by many different parties, this behavior cannot be 
   guaranteed.

   It is possible that the device firmware may save you, but this is device 
   dependent and untested. Be careful to prevent damaging devices with bad
   inputs.

.. note::

   You should always close connections to the device when you are finished.
   This will ensure proper recovery of resources and prevent access errors
   from subsequent connections.

   More important than closing connections, though, is making sure the hardware
   device is in a safe state. For example, a laser doesn't automatically turn
   off between runs. This is so if you disconnect but continue using it, you 
   don't have the pain of it automatically turning itself off. Additionally,
   there's often a time penalty for each reconnect; so the devices typically
   maintain their state when disconnected. So, be aware of your instruments!


.. currentmodule:: pyrolab

Base Instrument
---------------
.. currentmodule:: pyrolab.drivers
.. autosummary::
   :toctree: api/
   :recursive:

   Instrument

Cameras
-------
.. currentmodule:: pyrolab.drivers.cameras
.. autosummary::
   :toctree: api/
   :recursive:

   thorcam
   uc480
   sciTSI

Lasers
------
.. currentmodule:: pyrolab.drivers.lasers
.. autosummary::
   :toctree: api/

   tsl550
   ppcl55x

Scopes
------
.. currentmodule:: pyrolab.drivers.scopes
.. autosummary::
   :toctree: api/
   :recursive:

   rohdeschwarz

Source-Measure Units
--------------------
.. currentmodule:: pyrolab.drivers.smu
.. autosummary::
   :toctree: api/
   :recursive:

   keysight

Motion
------
.. currentmodule:: pyrolab.drivers.motion
.. autosummary::
   :toctree: api/
   :recursive:

   max31x
   prm1z8
   z8xx

Microcontrollers/Processors
----------------------------
.. currentmodule:: pyrolab.drivers.arduino
.. autosummary::
   :toctree: api/
   :recursive:

   arduino

FPGA's
------
.. currentmodule:: pyrolab.drivers.fpgas
.. autosummary::
   :toctree: api/
   :recursive:

   analogdiscovery

Mixins
------

Note that certain mixins will add functionality to services that are hosted
on a PyroLab network. Individually, the above drivers do not have these 
functions, and they are not available when the drivers are used locally. But,
some daemons add these mixins when hosting services. These functions then 
become available to the :py:class:`Proxy`. So, a list of mixins is maintained
here, as these functions are not documented with each driver but may be 
available to them.

* :py:class:`~pyrolab.server.Lockable`

Debugging/Sample Services
-------------------------
.. currentmodule:: pyrolab.drivers
.. autosummary::
   :toctree: api/
   :recursive:

   sample
