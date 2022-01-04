Server (and Service) Configuration
==================================

While servers, often referred to as daemons in the PyroLab docs, and services
registered through them can be thought about and developed separately, in
deployment, their configurations are inextricably linked. Hence this section
will again reference services, in addition to servers.

Server daemons and service configurations are only important for host machines
providing services to a PyroLab network. For a client simply connecting to the
network to utilize available PyroLab services, there is no need to configure
servers or services.

Let's take a look at the server configuration class, ``DaemonConfiguration``.

----

.. autoclass:: pyrolab.configure.DaemonConfiguration
   :members: __init__
   :noindex:

----

First, notice that all the configuration values have "sensible" defaults.
PyroLab by default keeps everything on localhost for security's sake---you 
don't want to unwittingly open up your ports to the world. You have to 
explicitly tell PyroLab to do that.

Second, notice that in a YAML representation of the nameserver's configuration, 
only the keys that are different from the defaults need to be defined; the
model that loads the file will automatically populate the missing fields with
the default values.

We can work with DaemonConfiguration objects either through a text YAML file,
or by constructing the actual Python object. Let's see how that would look:

.. code-block:: python
   :caption: The default server configuration, interacting directly with 
      the Python object.

   >>> from pyrolab.configure import DaemonConfiguration
   >>> config = DaemonConfiguration()
   >>> config.module, config.classname, config.host, config.port
   ('pyrolab.daemon', 'Daemon', 'localhost', 0)

.. code-block:: python
   :caption: Server configuration, interacting with the Python object, with
      values modified from the default.

   >>> from pyrolab.configure import DaemonConfiguration
   >>> config = DaemonConfiguration(classname="LockableDaemon", host="public", port=2022)
   >>> config.module, config.classname, config.host, config.port
   ('pyrolab.daemon', 'LockableDaemon', 'public', 2022)

These objects have a :py:func:`pyrolab.configure.YAMLMixin.yaml` method that 
can be used to dump the configuration to a valid YAML file. It can accept a 
parameter that allows you to dump only the values that differ from the default. 
Let's see how that would look:

.. code-block:: python
   :caption: The default server configuration, interacting with the YAML
      representation.

   >>> from pyrolab.configure import DaemonConfiguration
   >>> config = DaemonConfiguration()
   >>> print(config.yaml())
   module: pyrolab.server
   classname: Daemon
   host: localhost
   port: 0
   unixsocket: null
   nathost: null
   natport: 0
   servertype: thre

.. code-block:: python
   :caption: Modified server configuration, interacting with the YAML 
      representation, with defaults excluded.

   >>> from pyrolab.configure import DaemonConfiguration
   >>> config = DaemonConfiguration(classname="LockableDaemon", host="public", port=2022)
   >>> print(config.yaml(exclude_defaults=True))
   classname: LockableDaemon
   host: public
   port: 2022

.. You can run a simple server by simply passing one of these objects to 
.. :py:func:`pyrolab.nameserver.start_ns_loop`.

.. .. code-block:: python
..    :caption: Starting a nameserver, continuing using the config from above.

..    >>> from pyrolab.nameserver import start_ns_loop
..    >>> start_ns_loop(config)

.. So a complete script for starting up a nameserver that is visible to other 
.. machines on the network would look like this:

.. .. code-block:: python
..    :caption: Simplest, complete script for running a nameserver visible to 
..       other machines on the network.

..    >>> from pyrolab.configure import NameServerConfiguration
..    >>> from pyrolab.nameserver import start_ns_loop
..    >>> config = NameServerConfiguration(host="public")
..    >>> start_ns_loop(config)
