.. _getting_started_architecture:


Pyro5 Architecture
==================


On the shoulders of giants...
-----------------------------

Yes, we created PyroLab from scratch. No, we did not create the network
communication library from scratch.

`Pyro5`_ is a pure Python Remote Procedure Call (`RPC`_) library, licensed
under the MIT license.

.. _RPC: https://en.wikipedia.org/wiki/Remote_procedure_call
.. _Pyro5: http://pyro5.readthedocs.org/en/latest/


Definitions
-----------

There are four important concepts from Pyro5 that are important in PyroLab:

#. Services (remote resource implementations, instrument drivers, data processing routines)
#. Servers (machines that host remote resources, are physically connect to instruments, etc.)
#. Nameservers (an optional "phonebook" making locating servers and services easy)
#. Clients (machines that are aggregating and accessing remote resources)

PyroLab "services" are objects that are remotely accessible. These might be
hardware devices, long running calculations, or perhaps an interface providing
an API for interacting with filesystems on a remote machine; it all depends on
what methods your services provide. 

The machine that hosts your services is called a "server" and runs one or more
"daemon" processes that listen for requests on a port (one port per daemon).
Each daemon runs in its own process, so the failure of one daemon doesn't
affect another. Each daemon controls one or more services. Therefore, multiple
services can be accessed on the same IP address and the same port, but they
each have a unique Pyro URI that you connect with in order to send commands.
One computer may therefore have services accessible through multiple ports,
depending on how many daemons are configured. There are different run
configurations for daemons, which are described in detail in the `user guide
<user_guide_servers>`_.

A "nameserver" acts as a phonebook. Daemons can be configured to register
themselves with a nameserver when they're started up. In essence, they send a
notification to the server that they're up, and they send over a list of
services that can now be accessed. They provide the name of the service, as
well as a URI that can be fed to a Proxy, the object in PyroLab that a client
uses to directly connect to a service and call its methods. The nameserver does
nothing more than store names to URI's, and provide them upon request from a
client. Note that a nameserver doesn't have to be running on a separate 
machine; all parts of a PyroLab network could in theory be running on a single
machine. The fact that they interact by making requests that are handled on 
certain ports is what makes them a network.

A "client" is your local machine, when you're using it to connect to remote
resources. You access remote resources by using a
:py:class:`~pyrolab.api.Proxy`. A Proxy takes a URI that identifies a service
to be connected to. Usually, you will ask the nameserver for the location of
some service by using its "human-readable" name, but it will return a
(unwieldy) URI that is then fed into the Proxy. You can now call all the
publicly exposed methods of the service as if it were a local object running on
your own machine.


Network Architecture
--------------------

.. figure:: /_static/images/architecture.png
   :width: 600
   :alt: PyroLab architecture in the wild
   
   a. An example hardware setup. b. The interactions between objects in a 
   PyroLab network. A resource server is a "daemon."

When configuring a PyroLab network, you basically think about it in the 
following order:

#. Set up a nameserver to track available services.
#. Create some server daemons (called resource servers in the figure above)
   on your machines connected to specific hardware or providing specific
   computation functionality. 

   * The daemons will ping the nameserver to register themselves when they
     start up.

#. The nameserver will periodically check in with the daemons to make sure they
   haven't disappeared or gone offline. 

   * If they have gone offline, the nameserver can be configured to 
     automatically unregister them. Or, you might wish to keep a record of them 
     and their last known address in the nameserver registry.

#. Clients ping nameservers to get the URI address of services they wish to
   interact with.
#. Clients then communicate **directly** with daemons, which relay requests to
   services/hardware they host.

   * At this point, the nameserver is out of the picture! It only gives the URI
     to the client, which then *directly contacts* the service. The nameserver
     does not relay any of the requests.

You can see there is a triangle of communciation going on; nameservers and
daemons communicate, nameservers and clients communicate, and clients and
daemons communicate. None of the client communication with the daemon passes
through the nameserver, though. And finally, all communication with the service
itself is over-the-wire via the daemon; the nameserver and client never 
directly interact with a service, except through the daemon.
