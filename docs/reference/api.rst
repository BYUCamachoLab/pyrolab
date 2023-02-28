.. .. currentmodule:: pyrolab.api


pyrolab.api
===========

Importing ``pyrolab.api`` or any object from it has one (useful) side effect.
If a configuration file exists (has been set through the CLI), it will load and
set PyroLab to use the first listed nameserver configuration. Functions such as
:py:func:`pyrolab.api.locate_ns` will therefore find the nameserver
without needing to pass any arguments, such as the hostname of the nameserver.


Services
--------

Wrappers
~~~~~~~~

.. autofunction:: pyrolab.api.expose

.. autofunction:: pyrolab.api.behavior

.. autofunction:: pyrolab.api.oneway

Classes
~~~~~~~

* :py:class:`pyrolab.service.Service`


Server Daemon
-------------

Functions
~~~~~~~~~

.. autofunction:: pyrolab.api.locate_ns

.. autofunction:: pyrolab.api.start_ns

.. autofunction:: pyrolab.api.start_ns_loop

.. autofunction:: pyrolab.api.serve

Classes
~~~~~~~

* :py:class:`pyrolab.server.Daemon`
* :py:class:`pyrolab.server.LockableDaemon`


Client
------

Classes
~~~~~~~

.. autoclass:: pyrolab.api.Proxy


Configuration
-------------

Functions
~~~~~~~~~

* :py:func:`pyrolab.configure.update_config`
* :py:func:`pyrolab.configure.reset_config`

Classes
~~~~~~~

* :py:class:`pyrolab.configure.NameServerConfiguration`
* :py:class:`pyrolab.configure.DaemonConfiguration`
* :py:class:`pyrolab.configure.ServiceConfiguration`
* :py:class:`pyrolab.configure.PyroLabConfiguration`
