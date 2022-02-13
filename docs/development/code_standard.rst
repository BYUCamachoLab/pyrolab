================
Coding Standards
================

Docstring Standards
-------------------

This project strictly adheres to the numpydoc style guide.

Type Hinting
------------

We type hint all our functions and classes. This includes parameters, return
values, and some constants if it contributes to code clarity.

The numpydoc parser used to generate the documentation is clever enough to
remove the type hinting from the documentation, yielding clean looking 
documentation as well as clear code. The best of both worlds!

Logging
-------

All logging is done through the python logging module. Objects should log 
statements using the correct logging level corresponding to the severity of
the event. For example, a function may log at the DEBUG level the fact that
a function has been entered. Any time a server function is being attempted,
perhaps that's worthy of an INFO level event. Exceptions should be logged
with the ERROR level, using the logging module's :py:func:`logging.exception`.

It is especially important to use the logger because, since these processes
all run in separate threads or processes that are often windowless, they can
fail silently and without printing any error messages to the console. For the
sake of debugging, it is important to be able to review the logs to see at what
point the program failed.
