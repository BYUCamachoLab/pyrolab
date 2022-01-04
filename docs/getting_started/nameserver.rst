Nameserver Configuration
========================

A nameserver configuration is necessary whether it's on the machine actually
hosting a nameserver or on a machine that will be hosting services that will 
be registered with the nameserver. In either case, it uses the information
stored in a :py:class:`NameServerConfiguration` object to setup or locate 
nameservers.

Let's take a look at the nameserver configuration class.

----

.. autoclass:: pyrolab.configure.NameServerConfiguration
   :members: __init__
   :noindex:

----

Again, notice that all the configuration values have "sensible" defaults.
PyroLab by default keeps everything on localhost for security's sake.

As with the server configuration, in the YAML representation of the
nameserver's configuration, only the keys that are different from the defaults
need to be define. Undefined fields assume their default values.

We can work with NameServerConfiguration objects either through a text YAML
file, or by using the actual Python object. Let's see how that would look:

.. code-block:: python
   :caption: The default nameserver configuration, interacting directly with 
      the Python object.

   >>> from pyrolab.configure import NameServerConfiguration
   >>> config = NameServerConfiguration()
   >>> config.host, config.ns_port
   ('localhost', 9090)

.. code-block:: python
   :caption: Nameserver configuration, interacting with the Python object, with
      values modified from the default.

   >>> from pyrolab.configure import NameServerConfiguration
   >>> config = NameServerConfiguration(host="public", ns_port=2022, ns_autoclean=30.0, storage="sql")
   >>> config.host, config.ns_port
   ('public', 2022)

These objects have a :py:func:`pyrolab.configure.YAMLMixin.yaml` method that 
can be used to dump the configuration to a valid YAML file. It accepts a 
parameter that allows you to dump only the values that differ from the default. 
Let's see how that would look:

.. code-block:: python
   :caption: The default nameserver configuration, interacting with the YAML
      representation.

   >>> from pyrolab.configure import NameServerConfiguration
   >>> config = NameServerConfiguration()
   >>> print(config.yaml())
   host: localhost
   ns_port: 9090
   broadcast: false
   ns_bchost: null
   ns_bcport: 9091
   ns_autoclean: 0.0
   storage: memory

.. code-block:: python
   :caption: Modified nameserver configuration, interacting with the YAML 
      representation, with defaults excluded.

   >>> from pyrolab.configure import NameServerConfiguration
   >>> config = NameServerConfiguration(host="public", ns_port=2022, ns_autoclean=30.0, storage="sql")
   >>> print(config.yaml(exclude_defaults=True))
   host: public
   ns_port: 2022
   ns_autoclean: 30.0
   storage: sql

You can run a simple nameserver by simply passing one of these objects to 
:py:func:`pyrolab.nameserver.start_ns_loop`.

.. code-block:: python
   :caption: Starting a nameserver, continuing using the config from above.

   >>> from pyrolab.nameserver import start_ns_loop
   >>> start_ns_loop(config)

So a complete script for starting up a nameserver that is visible to other 
machines on the network would look like this:

.. code-block:: python
   :caption: Simplest, complete script for running a nameserver visible to 
      other machines on the network.

   >>> from pyrolab.configure import NameServerConfiguration
   >>> from pyrolab.nameserver import start_ns_loop
   >>> config = NameServerConfiguration(host="public")
   >>> start_ns_loop(config)
