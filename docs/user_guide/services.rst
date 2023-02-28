.. _user_guide_services:


Services
========

Communication between services should always use Python's builtin types,
since they have to be serializable, and Pyro5's serializer doesn't know how
to serialize custom types. 

It is useful to define functions or data structures that know how to serialize
and reinstantiate data. Many of PyroLab's internals utilize the Pydantic 
library, which can convert complex dataclass-type objects into dictionaries
that can easily be transmitted and reinstantiated from the dictionary.

Autoconnecting Services
-----------------------

Some services have a "connect" function. Typically, this is for hardware
devices that need to be connected to the computer using a serial connection or
some other protocol. Therefore, this function will need to be called before any
other functions can be called.

.. note::

    Something to consider when writing drivers is that in the connect()
    function, you should do some checking to see if it's already connected
    because if multiple connections request access, you want to be able to 
    handle them all gracefully instead of giving false unavailable errors.

In some cases, those connection parameters are computer-specific and not known
by the end user. This is because the drivers are written to be generic and
usableeven without remote PyroLab connections (i.e., they can be imported and
used locally in a script). Because of this, PyroLab services can be configured
with autoconnect parameters, allowing remote clients who do not know the local
connection details to simply call "autoconnect()" to connect to the service
(which in turn simply forwards the call to "connect()" with the appropriate
parameters, never exposing them to the client). They are specified in the 
YAML configuration file for the computing acting as a server. Here's an example
for a laser that takes a single parameter different from the default, the
COM port on which to connect:

.. code-block:: yaml

    services:
        westview.scarletwitch:
            module: pyrolab.drivers.lasers.tsl550
            classname: TSL550
            parameters:
                port: COM4
            description: Santec Laser
            instancemode: single
            daemon: westview.daemon
            nameservers:
            - production

Because of this mechanism, when writing services, all arguments to the function
should be keyword arguments (i.e. no positional arguments). They don't 
necessarily need to have *good* defaults, though; they could be values such as
None or an empty list, after which you have code in the connect function that
checks for bad arguments and raises exceptions like ValueError for required
arguments.


Availability
------------

Some services have drivers that may only be available on certain operating
systems. The beauty of PyroLab is that, while the computer hosting the service
must run the correct OS and provide the appropriate drivers, any client
(regardless of OS or the availability of drivers) can then connect to that
host via a Proxy and make requests, send control inputs, and retrieve data.


Exposing Methods
----------------

When writing drivers for instruments or other services, you should (as much
as possible) import from PyroLab's native API instead of directly importing 
from Pyro5. Some Pyro5 objects have had functions added to them to make them
work with PyroLab, and by using PyroLab versions of functions and objects, you
are future-proofing your code against potential changes that PyroLab might 
make. If you use the PyroLab versions, your code is sure to inherit whatever
functionality may be added.


.. _user_guide_instance_mode:

Instance Modes
--------------

.. todo:: 

    This section is under construction.


Exceptions
----------

Pyro5 only supports the serialization of builtin Python exception classes.
There is technically a way to register new serialization/deserialization 
functions with Pyro5, but since different versions of the software may be
running on each computer, the client would have to duplicate code for 
deserializing the attributes returned by the Proxy. Therefore, it is simpler
to restrict exceptions to builtins. 

The `Python builtin exception
<https://docs.python.org/3/library/exceptions.html>`_ list is pretty extensive,
and if you truly cannot find an existing exception that encapsulates the
essence of your error, you can always raise a generic exception with a specific
message and then compare error strings on the handling side.
