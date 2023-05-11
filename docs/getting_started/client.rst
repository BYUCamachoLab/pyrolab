.. _getting_started_client:


Client Tutorial
===============


Freeing resources
-----------------

While it's nice to have PyroLab installed on all the computers you plan to use
it from, it's not technically required; PyroLab simply wraps the default
Pyro5 :py:class:`~pyrolab.api.Proxy` object. It knows how to communicate with
PyroLab drivers just as well as the version imported from PyroLab. In all our
examples, however, we'll import the Proxy from ``pyrolab.api``.

At this point, we have a nameserver running on the default ``localhost`` 
address. The configuration file also used the default port, 9090. Because 
PyroLab daemons generate human-undreadable URI's for each service, we'll
use the nameserver to find our library service.

To connect to any PyroLab object, we use a Proxy. You use a Proxy even when 
you don't realize it, like connecting to the nameserver:

.. code-block:: python

    ns = locate_ns(host="localhost")

``locate_ns()`` returns a Proxy object. Proxies track a remote Pyro5 URI, but
they do not connect to the remote server until the first function call is made.
Servers have limited resources, in terms of sockets--they can only support a
limited number of connections at a time. If more clients connect to the name
server, or any Proxy, than the pool size allows, they will get a connection
error.

It is suggested you apply the following pattern when using the name server in
your code:

#. obtain a proxy for the NS
#. look up the stuff you need, store it
#. free the NS proxy
#. use the URI's/proxies you've just looked up

This makes sure your client code doesn't consume resources in the name server
for an excessive amount of time, and more importantly, frees up the limited
connection pool to let other clients get their turn. If you have a proxy to the
name server and you let it live for too long, it may eventually deny other
clients access to the name server because its connection pool is exhausted. So
if you don't need the proxy anymore, make sure to free it up.

The best way to do this is to use a context manager, which automatically 
handles disconnecting the connection for you:

.. code-block:: python

    from pyrolab.api import locate_ns

    with locate_ns(host="localhost") as ns:
        uri = ns.lookup("library")

    print(uri)
    # this URI will change every time, but this time it printed:
    # PYRO:obj_a488557cc38f4d149cdc1fdb38d75e27@localhost:50328

.. note::

    You can still use the proxy object when it is disconnected: Pyro will
    reconnect it for you as soon as it's needed again.

A similar pattern is recommended for drivers to which you make infrequent
calls:

.. code-block:: python

    from pyrolab.api import Proxy

    with Proxy(uri) as obj:
        obj.method()


Back to the library
-------------------

We can get our library instance and load it with our catalog to start:

.. code-block:: python

    from pyrolab.api import locate_ns, Proxy

    with locate_ns(host="localhost") as ns:
        uri = ns.lookup("library")

    with Proxy(uri) as catalog:
        books = {
            "The Hobbit": 3,
            "The Lord of the Rings": 2,
            "Harry Potter": 3,
            "The Lightning Thief": 2,
            "C Programming": 2,
        }

        for book, number in books.items():
            catalog.add_book(book, number)

Note that we freed our connection to the nameserver by using it as a context
manager, which automatically releases the connection upon exiting the block.
This is best practice, since once we get the URI the first time, we won't be
needing the nameserver again.

We then use the Proxy object, again in a context manager, to make several calls
with the same connection. No need to disconnect and reconnect between every
API call. It's less likely multiple clients will be trying to access the same
service simultaneously, anyway--especially in the context of PyroLab, which is
geared towards the remote control of hardware devices. Only one person will
be using them at a time.

We can now perform operations against our library. The Proxy acts like a local
Python object, exposing all the public methods that were marked with
``@expose`` (or all non-private functions if the entire class was decorated).
Because we used builtin Python exceptions in our class, we can also catch
exceptions we know will be raised if we perform illegal operations.

.. code-block:: python

    with Proxy(uri) as catalog:
        
        catalog.checkout("The Hobbit")

        catalog.checkout("C Programming", 2)

        # Check out a book when all books are already checked out
        try:
            catalog.checkout("C Programming")
        except ValueError as e:
            # handle this exception...

        # Return a book not in the library's catalog
        try:
            catalog.checkin("Dune")
        except LookupError as e:
            # handle this exception...

        # Check out a book not in the library's catalog
        try: 
            catalog.checkout("Coding for Dummies")
        except LookupError as e:
            # handle this exception...

Voila! We now have remote resources available on any client computer as a local
object. This opens up a world of possibilities when it comes to making multiple
hardware sources cooperate as a single operation. As a completely random
example, you might create a photonic chip testing station where one computer
controls motion stages, another controls a laser source, while yet another
provides a microscope image of the alignment, all being aggregated and
controlled by an untethered, underpowered laptop in a laboratory setting.

Continue on for a summary of what we've done in this getting started guide.
