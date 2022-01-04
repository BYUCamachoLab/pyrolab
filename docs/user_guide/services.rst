
Services
========

Communication between services should always use Python's builtin types,
since they have to be serializable, and Pyro5's serializer doesn't know how
to serialize custom types. 

It is useful to define functions or data structures that know how to serialize
and reinstantiate data. Many of PyroLab's internals utilize the Pydantic 
library, which can convert complex dataclass-type objects into dictionaries
that can easily be transmitted and reinstantiated from the dictionary.

Autoconnecting Services
-----------------------

Some services have a "connect" function. Typically, this is for hardware 
devices that need to be connected to the computer. This function should be
called before any other functions are called.

In some cases, those connection parameters are computer-specific and not known
by the end user. This is because the drivers are written to be generic and not
necessarily used with remote PyroLab connections (i.e., they can be imported
and used locally in a script). Because of this, PyroLab services can be 
configured with autoconnect parameters, allowing remote clients to simply call
"autoconnect()" to connect to the service (which in turn simply forwards the
call to "connect()" with the appropriate parameters, never exposing them to
the client).

Because of this mechanism, when writing services, all arguments to the function
should be keyword arguments (i.e. no positional arguments). They don't 
necessarily need to have *good* defaults, though; they could be values such as
None or an empty list, after which you have code in the connect function that
checks for bad arguments and raises exceptions like ValueError for required
arguments.