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

