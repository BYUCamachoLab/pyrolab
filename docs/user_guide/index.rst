.. _user_guide:

==========
User Guide
==========

.. toctree::
   :maxdepth: 2
   :hidden:

   nameservers
   servers
   clients
   
A few notes on simply starting Pyrolab. When launched from the terminal,
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

This can be very helpful when debugging to see how the program is progressing,
and when the program is being too verbose, it's easy to silence. Note that
including debugging will also include log statements from all of PyroLab's
dependencies.
