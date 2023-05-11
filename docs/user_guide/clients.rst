
Clients
=======

Since clients are simply Proxy objects that receive a list of available
functions when they first connect, they are PyroLab version-independent.

Note that it's always a good idea to use proxies in a context-manager to clean
up the connection:

.. code-block:: python

    with locate_ns(host="...") as ns:
        uri = ns.lookup("...")

    with Proxy(uri) as remote_object:
        remote_object.useful_method()

Assuming drivers and services have been written correctly, they only raise
builtin Python exceptions. You can also catch different levels of exceptions if
you know what exceptions an object can raise. Therefore you can use them in
try-except blocks:

.. code-block:: python

    try:
        remote_object.useful_method()
    except ConnectionError as e:
        # handle this kind of error
    except Exception as e:
        # handle the generic exception
