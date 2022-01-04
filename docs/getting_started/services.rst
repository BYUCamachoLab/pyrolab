.. _getting_started_services:


Services
========

In this example, we'll write a simple service that performs a potential "real-
world" application in a very bad, overly simplistic way. But the goal is to
learn the API of services, not actually implement a good service.


The Library Problem
-------------------

For this demonstration, let's assume there's a service that acts as a
library registry. It'll maintain a list of all available books and their
quantities. We won't use a real database; we'll just an in-memory Python
dictionary. Every time your service is shutdown and restarted, you'll lose
the state of the "database." Oh well. Let's get started!

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

Let's write a simple Python class that can do this:

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
                raise ValueError(f"Cannot checkout: Book '{title}' not found.")
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
                raise ValueError(f"Cannot checkin: Book '{title}' not found.")
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
                raise ValueError(f"Cannot remove: Book '{title}' not found.")
            del self.catalog[title]

   

Pyro-ing it
-----------

To make a class Pyro compatible, there's a few things you should note:

* Only accept and return standard Python builtin types. These are the only 
  things the Pyro5 serializer knows how to handle and pass across a network.
* You can expose certain methods and properties from the class, or you can
  expose an entire class and all its PUBLIC methods and properties will be
  exposed.
* Private methods and properties CANNOT be exposed (methods that start with an
  underscore). You CAN expose dunder methods (special methods that start and
  end with a double underscore, e.g. ``__len__``).

You need to decorate your class with ``@expose`` to make it Pyro-compatible.

PyroLab also provides a :py:class:`Service` class that should be used as a base
object that your service inherits from. While the base class won't expose any
of your methods for you, it does add some functionality that PyroLab can use in
the background, as well as some convenience methods for you (such as a function
for setting the instance mode behavior of the class, see the `user guide
<user_guide_servers>`_ for advanced usage).

Our class from above is already safe in the sense that it only accepts and
returns regular Python types. Now, we can simply change its base and add the
``@expose`` decorator so that a PyroLab server could host it. Additionally,
since we don't want to create a new object for every incoming Proxy connection,
but one object for all incoming connections, we'll use the ``@behavior``
decorator to set the instance mode to "single". (If we were to create a new
object for every Proxy connection, our libraries wouldn't actually be in sync
with each other.) Again, see the `user guide <user_guide_servers>`_ for more
information on behaviors.

.. code-block:: python

    from pyrolab.api import Service, expose, behavior

    @behavior(instance_mode="single")
    @expose
    class LibraryCatalog(Service):
        ...

We now have a PyroLab service class! Continue reading to learn how to host it
for remote clients.
