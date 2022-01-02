.. _api.drivers:

pyrolab.drivers
===============
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

Mixins
------

Note that certain mixins will add functionality to services that are hosted
on a PyroLab network. Individually, the above drivers do not have these 
functions, and they are not available when the drivers are used locally. But,
some daemons add these mixins when hosting services. These functions then 
become available to the :py:class:`Proxy`. So, a list of mixins is maintained
here, as these functions are not documented with each driver but may be 
available to them.

* :py:class:`pyrolab.daemon.Lockable`

Debugging/Sample Services
-------------------------
.. currentmodule:: pyrolab.drivers
.. autosummary::
   :toctree: api/
   :recursive:

   sample
