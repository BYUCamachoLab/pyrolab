This is a simple example to help you test a sample Instrument with autoconnect
parameters.

For a typical setup:
    1. Some publicly visible server will host "nameserver.py". 
    2. The instrument connected to a computer will run "server.py".
    3. Your local computer will connect to remote resources as
       demonstrated in "client.py".

To test these, 3 terminal tabs are desirable, with commands executed
in each in the following order:
    1. ``python nameserver.py``
    2. ``python server.py``
    3. ``python client.py``

Note that the AutoconnectLockableDaemon used in ``server.py`` only supports the
registration of a single object. When registering with the daemon, a dictionary
of connection parameters can be provided. This must be a complete dictionary;
that is, all parameters from an Instrument's ``connect()`` function must be
explicitly specified in the dictionary; no default values will be assumed.

Note that metadata on the nameserver for an Instrument supporting 
``autoconnect()`` usually explicitly states that that is the case.