.. currentmodule:: pyrolab.api


pyrolab.api
===========

Importing ``pyrolab.api`` or any object from it has one (useful) side effect.
If a configuration file exists (has been set through the CLI), it will load
and set PyroLab to use the first listed nameserver configuration. Functions
such as :py:func:`pyrolab.nameserver.locate_ns` will find the nameserver without needing to
pass any arguments, such as the hostname of the nameserver.


Services
--------

* :py:func:`pyrolab.server.expose`
* :py:func:`pyrolab.server.behavior`
* :py:func:`pyrolab.server.oneway`

* :py:class:`pyrolab.service.Service`
* :py:class:`pyrolab.api.Proxy`

Server
------

* :py:func:`pyrolab.api.locate_ns`
* :py:func:`pyrolab.nameserver.start_ns`
* :py:func:`pyrolab.nameserver.start_ns_loop`
* :py:func:`pyrolab.server.serve`

* :py:class:`pyrolab.server.Daemon`
* :py:class:`pyrolab.server.LockableDaemon`

Configuration
-------------

* :py:func:`pyrolab.configure.update_config`
* :py:func:`pyrolab.configure.reset_config`

* :py:class:`pyrolab.configure.NameServerConfiguration`
* :py:class:`pyrolab.configure.DaemonConfiguration`
* :py:class:`pyrolab.configure.ServiceConfiguration`
* :py:class:`pyrolab.configure.PyroLabConfiguration`
