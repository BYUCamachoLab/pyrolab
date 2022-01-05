.. _user_guide_nameservers:


Nameservers
===========

A Pyro Nameserver is a tool to help keeping track of your objects in your
network. It is also a means to give your Pyro objects logical names instead of
the need to always know the exact object name (or id) and its location.

PyroLab supports hosting multiple nameservers on a single computer, as long as
they are bound to different ports. This is useful for isolating different lab
environments without the need to set up multiple computers.

In order to configure a nameserver, you need to write a YAML nameserver 
configuration file. By default, unknown options are simply ignored (although 
PyroLab can be set to raise an Exception), so spell carefully. It has the 
following options:

host
    The hostname or ip address that the nameserver will bind on (being a
    regular Pyro daemon). Defaults to localhost.
ns_port
    The port number where the nameserver should listen. Defaults to 9090.
ns_bchost
    The hostname or ip address of the nameserver's broadcast responder.
    Defaults to 9091.
ns_bcport
    The port number of the nameserver's broadcast responder. Defaults to null
    (no broadcast responder).
ns_autoclean
    A recurring period in seconds where the Name server checks its
    registrations, and removes the ones that are no longer available. Defaults
    to 0.0 (off).
storage_type
    Specify the storage mechanism to use. You have several options:

    * ``memory``: fast, volatile in-memory database. This is the default.
    * ``dbm``: dbm-style persistent database table. Filename must be provided
      (see the ``storage_file`` option). This storage type does not support metadata.
    * ``sql``: sqlite persistent database. Filename must be provided 
      (see the ``storage_file`` option).
storage_file
    The filename (full path) to use for the storage if the mechanism is not 
    ``memory``. Default is an automatic program data directory, so does not 
    need to be provided. Ignored for ``memory`` storage.


Configuring a nameserver
------------------------

An example nameserver configuration file might then contain something like
this:

.. code-block:: yaml

    nameservers:
        - default:
            host: localhost
            ns_port: 9090
            ns_bchost: localhost
            ns_bcport: 9091
            ns_autoclean: 0.0
            storage_type: memory
        - production:
            host: camacholab.ee.byu.edu
            ns_port: 9090
            ns_bchost: null
            ns_bcport: 9091
            ns_autoclean: 15.0
            storage_type: sql
        - development:
            host: localhost
            ns_port: 9090


Launching a nameserver
-----------------------

Using the command line interface
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If PyroLab is installed in the system path and a configuration file exists 
(either internally within PyroLab or at a location you specify), you can launch 
a nameserver with the following command:

.. code-block:: bash

    $ pyrolab nameserver -c ./ns_cfg.yml -l production


Using a script
^^^^^^^^^^^^^^
In order to start up a nameserver using Python code, you could write a small 
script like this:

.. code-block:: python

    from pyrolab.nameserver import read_nameserver_configs, start_ns_loop

    configs = read_nameserver_configs("./ns_cfg.yml")
    start_ns_loop(configs['default'])


Notes on nameserver registrations
---------------------------------

Because many services may "go dark" or become unavailable at times, the 
nameserver can be configured to "autoclean" itself. Additionally, PyroLab
does its best to ensure that as services are shutdown, they also notify the
nameserver that they're are no longer available and should be removed. However,
sometimes the software (or the hardware) may crash without the chance to 
handle housekeeping calls. This is why the nameserver can periodically ping
all known services to check if they are still alive.

Additionally, because services can come back online with the same name and
notify the nameserver of their availability, the nameserver will not block
registrations of new services with the same name. Be sure when you're writing
a configuration file with daemons and services that you check to make sure
none of the names you're using are already used by the register, or you may
"orphan" some services, in the sense that they'll be unfindable by others!
