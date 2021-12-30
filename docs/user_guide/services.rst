
Services
========

Communication between services should always use Python's builtin types,
since they have to be serializable, and Pyro5's serializer doesn't know how
to serialize custom types. 

It is useful to define functions or data structures that know how to serialize
and reinstantiate data. Many of PyroLab's internals utilize the Pydantic 
library, which can convert complex dataclass-type objects into dictionaries
that can easily be transmitted and reinstantiated from the dictionary.
