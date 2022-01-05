.. _getting_started_pyro5:


Pyro5 Essentials
================

On the shoulders of giants...
-----------------------------

Yes, we created PyroLab from scratch. No, we did not create the network
communication library from scratch.

`Pyro5`_ is essentially a pure Python Remote Procedure Call (`RPC`_) library, 
licensed under the MIT license.

.. _RPC: https://en.wikipedia.org/wiki/Remote_procedure_call
.. _Pyro5: http://pyro5.readthedocs.org/en/latest/


There are three important concepts from Pyro5 that are important in PyroLab:

#. Services
#. Servers
#. Nameservers

PyroLab "services" are objects that are remotely accessible. These might be
representative of hardware devices, long running calculations, or perhaps an
object providing an API for interacting with filesystems on a remote machine;
it all depends on what methods your services provide. 

The program that hosts your services is called a "server" and runs daemon
processes that listen for requests. Services are registered with a daemon, and
a single machine could host multiple daemons. There are different run
configurations for daemons, which are described in detail in the `user guide
<user_guide_servers>`_.

