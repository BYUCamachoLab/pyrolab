.. _user_guide:


Environment Variables
=====================
   
A few notes on simply starting PyroLab. When launched from the terminal,
PyroLab reads a few environment variables for convenient configuration.

.. todo::
   
   Link to where the data directories is discussed, for appdirs.

``PYROLAB_LOGFILE``
   The log file to write to. If not set, the default is ``pyrolab.log``
   within PyroLab's default data directory (see appdirs).
``PYROLAB_LOGLEVEL``
   The log level to use. If not set, the default is ``INFO``.
``PYROLAB_HUSH_DEPRECATION``
   If set, silences all DeprecationWarnings from all modules.
``PYROLAB_NO_VERSION_CHECK``
   If set (to any value), the ``pyrolab`` command line tool never checks PyPI
   for a newer release. Otherwise it checks at most once a day, with a short
   timeout, and caches the result (including a failed check) so that machines
   on isolated networks don't wait on every command. Importing ``pyrolab`` as
   a library never checks.

This can be very helpful when debugging to see how the program is progressing,
and when the program is being too verbose, it's easy to silence. Note that
including debugging will also include log statements from all of PyroLab's
dependencies.
