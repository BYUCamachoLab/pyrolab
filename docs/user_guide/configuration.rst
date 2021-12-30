Nameservers
===========

Note that, regardless of whether it is present in the file, the default
configuration is always available. It has the following settings:

.. code-block:: yaml
    nameservers:
        - default:
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

Note that, regardless of whether it is present in the file, the default
configuration is always available. It has the following settings:

.. code-block:: yaml
    daemons:
        - default:
            classname: Daemon
            host: localhost
            servertype: thread

If a profile named "default" exists in the file, the base default is 
overridden. Many places in PyroLab read the default configuration, so be
careful and make sure you actually want to change the default.



You can also specify "auto n" where n is an integer to generate a
random name of n words for any kind of object.
