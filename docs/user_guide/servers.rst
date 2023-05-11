.. _user_guide_servers:

Servers
=======

What's a PyroLab server?
------------------------

A server in PyroLab parlance is a constantly-running, constantly-listening
(typically backgrounded) process that runs on a remote machine and provides
services to a PyroLab network. A server is an instance of a
:py:class:`pyrolab.server.Daemon`. PyroLab enables you to configure multiple
daemons to run on a single host (each daemon opens up a different network
port), and each daemon can provide multiple services. This allows you to start
up new services on a new daemon without interfering with existing services,
group related services together, or create dedicated processes for certain
services.

Additionally, there are different types of daemons with different features---
for example, regular Pyro5 daemons that provide services accessible by multiple
users simultaneously, or PyroLab-specific daemons that allow services to be
locked by a user and only accessible by that user. These daemons also include 
logic that automatically frees services upon user disconnect, in case they 
forget to unlock it themselves.

PyroLab hosts can be configured with a file that details which daemons and
services (such as hardware devices) to automatically start when the host is
started. In this way, PyroLab can easily be shutdown and restarted without
having to run lengthy Python scripts. Failures that result in the termination
of PyroLab processes, such as power outages, are easily recovered from; since
the connected instruments are known to the program, it can reload them
automatically upon startup, registering them again with the appropriate
:ref:`nameserver <user_guide_nameservers>` (see how to configure your machine
to automatically start PyroLab on startup at :ref:`Deployment
<user_guide_deployment>`).

Another reason to split services up between different daemons is because any
given daemon can run in one of two ``servertype`` modes.


Server types (and concurrency)
------------------------------

As described by the Pyro5 docs:

#. Threaded server (default)

   This server uses a dynamically adjusted thread pool to handle incoming proxy
   connections. If the max size of the thread pool is too small for the number
   of proxy connections, new proxy connections will fail with an exception. The
   size of the pool is configurable via some config items:

   * ``THREADPOOL_SIZE`` this is the maximum number of threads that Pyro will use
   * ``THREADPOOL_SIZE_MIN`` this is the minimum number of threads that must remain standby

   Every proxy on a client that connects to the daemon will be assigned to a
   thread to handle the remote method calls. This way multiple calls can
   potentially be processed concurrently. This means your Pyro object may have
   to be made thread-safe! If you registered the pyro object's class with
   instance mode ``single``, that single instance will be called concurrently from
   different threads. If you used instance mode ``session`` or ``percall``, the
   instance will not be called from different threads because a new one is made
   per connection or even per call. But in every case, if you access a shared
   resource from your Pyro object, you may need to take thread locking measures
   such as using Queues.

   **ASIDE:** For PyroLab's main use case, typically hardware devices,
   registering devices with instance mode ``single`` and using a lockable
   daemon that prevents more than one client from accessing the service is the
   most appropriate usage and will relieve you from the pain of thinking about
   thread-safety.

#. Multiplexed server

   This server uses a connection multiplexer to process all remote method calls
   sequentially. No threads are used in this server. It uses the best supported
   selector available on your platform (kqueue, poll, select). It means only
   one method call is running at a time, so if it takes a while to complete,
   all other calls are waiting for their turn (even when they are from
   different proxies). The instance mode used for registering your class, won't
   change the way the concurrent access to the instance is done: in all cases,
   there is only one call active at all times. Your objects will never be
   called concurrently from different threads, because there are no threads. It
   does still affect when and how often Pyro creates an instance of your class.

So, if you have multiple services on a threaded server, calls can execute 
simultaneously. But if you have multiple services on a multiplexed server,
calls will execute one after the other, and will wait for all previous calls
to execute, too.

Be aware when you define your daemons that you don't define too many; each 
will be started as a separate process, so if you're running a lot of daemons,
they won't actually be running simultaneously; your computer doesn't have
enough processors. *Most of the time*, you can just put all the services on a
threaded server. It's in the situation of a long-running function that blocks
where you might consider separating services between daemons so that you don't
lose the ability to contact other services or functions while awaiting the
return value of a blocking function.
