Configuration
=============


Nameservers
-----------

Note that, regardless of whether it is present in the file, the default
configuration is always available. It has the following settings:

.. code-block:: yaml
    
    nameservers:
        default:
            host: localhost
            broadcast: false
            ns_port: 9090
            ns_bchost: localhost
            ns_bcport: 9091
            ns_autoclean: 0.0
            storage_type: sql
            storage_filename: <pyrolab default data directory>

If a profile named "default" exists in the file, the base default is 
overridden. Many places in PyroLab read the default configuration, so be
careful and make sure you actually want to change the default.


Daemons
-------

Note that, regardless of whether it is present in the file, the default
configuration is always available. It has the following settings:

.. code-block:: yaml
    
    daemons:
        default:
            classname: Daemon
            host: localhost
            servertype: thread

If a profile named "default" exists in the file, the base default is 
overridden. Many places in PyroLab read the default configuration, so be
careful and make sure you actually want to change the default.


Services
--------

.. todo::

    Coming soon.


Choosing ``host``
-----------------

A nameserver or daemon listens on the address given by ``host``, and the URIs
it publishes contain that address, so it must be one that *clients* can reach.
Clients only ever connect to the PyroLab machine; instruments are reached by
that machine, not by clients.

``localhost``
    Only programs on the same machine can connect (the default).
``public``
    PyroLab picks this machine's address on the network that routes to the
    internet. On a machine without a route outside (an isolated lab network)
    it falls back to the address the machine's hostname resolves to, then to
    ``127.0.0.1``, and logs a warning.
an IP address or hostname
    Use this when the machine is on several networks and the clients are not
    on the internet-facing one, e.g. a private lab network on a second
    network card.
