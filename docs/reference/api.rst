.. currentmodule:: pyrolab.api


API
===

Importing ``pyrolab.api`` or any object from it has one (useful) side effect.
If a configuration file exists (has been set through the CLI), it will load
and set PyroLab to use the first listed nameserver configuration. Functions
such as :py:func:`locate_ns` will find the nameserver without needing to
pass any arguments, such as the hostname of the nameserver.


Services
--------

* :py:func:`expose`
* :py:func:`behavior`
* :py:func:`oneway`

* :py:class:`Service`
* :py:class:`Proxy`

Server
------

* :py:func:`locate_ns`
* :py:func:`start_ns`
* :py:func:`start_ns_loop`
* :py:func:`serve`

* :py:class:`Daemon`
* :py:class:`LockableDaemon`

Configuration
-------------

* :py:func:`update_config`
* :py:func:`reset_config`

* :py:class:`NameServerConfiguration`
* :py:class:`DaemonConfiguration`
* :py:class:`ServiceConfiguration`
* :py:class:`PyroLabConfiguration`
