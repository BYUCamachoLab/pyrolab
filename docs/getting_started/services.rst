.. _getting_started_services:


Writing Services
================

In this example, we'll write a simple service that performs a potential
"real-world" application in a very bad, overly simplistic way. But the goal is
to learn the API of services, not actually implement a good service.


The Library Problem
-------------------

Let's assume there's a service that acts as a library catalog. It'll maintain
a list of all available books and their quantities. We won't use a real
database; we'll just an in-memory Python dictionary. Every time your service is
shutdown and restarted, you'll lose the state of the "database." Oh well. Let's
get started!

.. figure:: /_static/images/ohnoanyway.png
   :width: 300
   :alt: Oh no! Anyway... (Top Gear)
   
   *Infinite books, if the power keeps going out.*

This example can also be found in the ``examples/library-catalog`` directory in
the PyroLab repository.


Defining the Class
------------------

Requirements:

* Keep track of all existing books
* Keep track of all available quantities/copies
* Checkout books, and decrement the quantity
* Return books, and increment the quantity
* Add new books to the registry
* Remove books from the registry

Let's write a simple Python class that can do this. We'll name the module
``libservice.py``:

.. code-block:: python
   
    class LibraryCatalog:
        """
        Simulates a library catalog, provides a way to check out and check in books.

        It's a bad library; it doesn't know who checked out the books, or how many
        books are missing from its collection. It just knows how many it has.

        Parameters
        ----------
        catalog : Dict[str, int]
            A dictionary of book titles and their quantities.
        """
        def __init__(self, catalog: Dict[str, int] = {}) -> None:
            self.catalog = catalog

        def get_catalog(self) -> Dict[str, int]:
            """
            Get the current catalog of books and their available quantities.

            Returns
            -------
            catalog : Dict[str, int]
                A dictionary of book titles and their quantities.
            """
            return self.catalog
        
        def checkout(self, title: str, quantity: int = 1) -> None:
            """
            Check out a book title.
            
            Parameters
            ----------
            title : str
                The title of the book to check out.
            quantity : int
                The number of copies to check out (default 1).
            """
            if title not in self.catalog:
                raise LookupError(f"Cannot checkout: Book '{title}' not found.")
            if self.catalog[title] < quantity:
                raise ValueError(f"Cannot checkout: Not enough copies of {title}.")
            self.catalog[title] -= quantity

        def checkin(self, title: str, quantity: int = 1) -> None:
            """
            Check in a book title.
            
            Parameters
            ----------
            title : str
                The title of the book to check in.
            quantity : int
                The number of copies to check in (default 1).
            """
            if title not in self.catalog:
                raise LookupError(f"Cannot checkin: Book '{title}' not found.")
            self.catalog[title] += quantity

        def add_book(self, title: str, quantity: int = 1) -> None:
            """
            Add a book to the catalog.

            Parameters
            ----------
            title : str
                The title of the book to add.
            quantity : int
                The number of copies to add (default 1).
            """
            self.catalog[title] = quantity

        def remove_book(self, title: str) -> None:
            """
            Permanently remove a book from the catalog.

            Parameters
            ----------
            title : str
                The title of the book to remove.
            """
            if title not in self.catalog:
                raise LookupError(f"Cannot remove: Book '{title}' not found.")
            del self.catalog[title]

.. warning::

    When naming your modules, take care to make sure no module names overlap
    with submodules of PyroLab, or the dynamic module loader may mistakenly
    load the wrong file!
   

Pyro-ing it
-----------

To make a class Pyro compatible, there's a few things you should note:

* Only accept and return standard Python builtin types. These are the only 
  things the Pyro5 serializer knows how to handle and pass across a network.
  (Even numpy arrays should be converted to a regular list.)
* You can expose certain methods and properties from the class, or you can
  expose an entire class and all its PUBLIC methods and properties will be
  exposed.
* Private methods and properties CANNOT be exposed (methods that start with an
  underscore). You CAN expose "dunder" methods (special methods that start and
  end with a double underscore, e.g. ``__len__``).
* If you're going to use exceptions, only use the `built-in Python exceptions
  <https://docs.python.org/3/library/exceptions.html>`_. These are the only
  ones that PyroLab knows how to serialize.

You need to decorate your class (or just the specific methods you want to make
publicly available) with ``@``:py:func:`~pyrolab.api.expose` to make it
Pyro-compatible.

PyroLab also provides a :py:class:`~pyrolab.service.Service` class that should
be used as a base object that your service inherits from. While the base class
won't expose any of your methods for you, it does add some functionality that
PyroLab can use in the background, as well as some convenience methods for you,
including:

* A :py:meth:`~pyrolab.service.Service.ping` method, so you can test the
  ability to connect with it quickly (the web monitor also uses this to check
  on services' availability, if you choose to set up the server).
* A function for setting the instance mode behavior of the class (see the `user
  guide <user_guide_instance_mode>`_ for advanced usage).

Our class from above is already safe in the sense that it only accepts and
returns regular Python types. Now, we can simply change its base and add the
``@``:py:func:`~pyrolab.api.expose` decorator so that a PyroLab server could
host it. Additionally, since we don't want to create a new object for every
incoming Proxy connection, but one object for all incoming connections, we'll
use the ``@``:py:func:`~pyrolab.api.behavior` decorator to set the instance
mode to "single". (If we were to create a new object for every Proxy
connection, our libraries wouldn't actually be in sync with each other--every
new connection would get the default initialization catalog.) This would be
especially important, for example, if you're working with physical hardware, of
which there only exists one and creating a new object for every connection
doesn't map to physical reality (unless we live in a multiverse where every
time you create a new connection with PyroLab it also duplicates a new piece of
that hardware in your lab). Again, see the `user guide
<user_guide_instance_mode>`_ for more information on behaviors.

Let's modify our class from above by adding the decorators and inheriting from 
the :py:class:`~pyrolab.service.Service` class:

.. code-block:: python

    from pyrolab.api import Service, expose, behavior

    @behavior(instance_mode="single")
    @expose
    class LibraryCatalog(Service):
        ...

We now have a new PyroLab service! In the next section, we'll learn how to host
it to allow remote clients to access it.
