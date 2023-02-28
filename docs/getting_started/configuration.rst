.. _getting_started_configuration:

Launch Configuration
====================


Making our services discoverable
--------------------------------

In order to use your own custom drivers and services with PyroLab, they have to
be visible to the Python interpreter. This means they must be either
installable (using pip install) or be in one way or another discoverable by the
Python interpreter; for example, being placed in the environment variable
``$PYTHONPATH``. On \*nix systems, this can be done by placing a statement in
your ``~/.bashrc`` file similar to the following:

.. code-block:: bash

    export PYTHONPATH="/path/to/your/services:$PYTHONPATH"

Another way of doing this is with a simple script that modifies your
environment variables for the lifetime of that shell. Then it's not globally
available all of the time. A simple script which does this is in the 
``library-catalog`` example directory:

.. literalinclude:: /../examples/library-catalog/updatepath.sh
    :language: bash

This prepends the directory containing the script (and presumably the Python
module ``service.py`` which contains the library catalog code) to the
``$PYTHONPATH`` variable. You'll now need to make sure you source the
``updatepath.sh`` script so that our service is discoverable. In the terminal,
navigate to the directory containing the library-catalog example and source the
script:

.. code-block:: bash

    source updatepath.sh

.. note::

    For the sake of this example, it's easiest to run these scripts on Windows
    Subsystem for Linux (WSL). Paths are much easier to manage in Linux. If you
    want to figure out how to do it on Windows, have fun!


.. _getting_started_yaml:

YAML launch configuration
-------------------------

PyroLab reads a YAML configuration file in order to start up server daemons and 
locate nameservers. In addition to a version number for future compatability
changes, it has four sections:

* nameservers
* daemons
* services
* autolaunch

Below is a fully functioning configuration example continuing from our library
example (see ``examples/library-catalog`` in the PyroLab repository) that you
could test on your own computer. It uses only included dependencies, our toy
library service, and runs on localhost. It automatically starts up the
nameserver and background services and daemons when you run ``pyrolab up``
(we'll discuss the command line interface more in the next section). 

This configuration will start the nameserver on localhost, although to make it
publicly available on the network you could simply change the key "host" from 
"localhost" to "public". Even though everything is running locally on your
computer, it simulates computers connecting over the network by binding to 
specific exposed ports.

An explanation of the sections follows the YAML file (here's ``config.yaml``): 

.. literalinclude:: /../examples/library-catalog/config.yaml
    :language: yaml

The ``nameservers`` option defines named nameservers either for starting up a
nameserver or for registering daemons and services with. Since the nameserver
is just a phonebook and doesn't manage daemons or services in any way, daemons
and services can be registered with any number of nameservers. Hence, the 
``nameservers`` section can contain multiple nameserver definitions.

The ``daemons`` section sets up a series of server daemons. Each daemon binds
to a different port on your system and runs as its own process. All services
hosted by a given daemon pass their communications through the one port. This
allows you to distribute your services across multiple daemons, so if one fails
not all are affected, or if one is particularly communication heavy, you can 
reduce latency to other services by having them on different interfaces where
they won't be blocked by some long running communication. Additionally, there
are specialty daemons that support different features, like device connection
locking. You might set up two daemons where one doesn't allow its devices to be
locked while the other does.

The ``services`` section defines services or hardware devices and the daemon
they should be hosted on. Each service belongs to a single daemon, but can be
registered with multiple nameservers. Since the class that defines the service
is dynamically loaded, this is why the Python module must be visible to the
interpreter.

The name of each service you provide is the name that the daemon will use to
register the service with the nameserver. 

.. warning::

    The nameserver doesn't care if you register a second service with the same
    name! It will happily overwrite the previous entry with the "updated"
    address. Make sure you're not reusing names with a nameserver, or you'll
    orphan your services--they'll be undiscoverable.

For the above reason, it may be useful to invent some sort of standardized
naming scheme for naming services. For example, in our setting, each computer
has a name (in our case, taken from the Marvel Cinematic Universe) and each
hardware device has a name, so we might end up with an entry like:

.. code-block:: yaml

    services:
      westview.scarletwitch:
        module: pyrolab.drivers.lasers.tsl550
        classname: TSL550
        parameters:
          port: ...
        description: Santec Laser
        instancemode: single
        daemon: westview.daemon
        nameservers:
        - ...

The ``autolaunch`` section defines servers to launch when the main PyroLab
daemon is started. It's possible to define services but launch and quit them
independently, similar to Docker containers. Having the configuration available
to PyroLab makes different servers known to PyroLab but doesn't automatically
mean they launch at startup. The ``autolaunch`` section allows us to mass
launch servers instead of starting them up one at a time.

In the next section, we'll use the PyroLab CLI to actually start up our 
services.
