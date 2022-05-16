Combined YAML Configuration
===========================

Below is a fully functioning example that you could test on your own computer.
It uses only included dependencies and sample services and runs on localhost.
It automatically starts up the nameserver and background services and daemons
when you run ``pyrolab up``.

.. code-block:: yaml
    
    version: '1.0'

    nameservers:
    production:
        host: localhost
        ns_port: 9090
        broadcast: false
        ns_bchost: null
        ns_bcport: 9091
        ns_autoclean: 0.0
        storage: memory

    daemons:
    lockable:
        module: pyrolab.server
        classname: LockableDaemon
        host: localhost
        port: 0
        unixsocket: null
        nathost: null
        natport: 0
        servertype: thread
        nameservers:
        - production

    services:
    pymtech.thething:
        module: pyrolab.drivers.sample
        classname: SampleService
        description: Sample service
        instancemode: single
        daemon: lockable
        nameservers:
        - production

    autolaunch:
    nameservers: 
    - production
    daemons:
    - lockable