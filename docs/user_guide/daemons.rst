
Configuring Servers
===================

PyroLab allows computers to be configured as servers that remember the devices
connected to them between sessions and shutdowns. These devices are 
automatically reexposed upon restart of the computer.

Be aware when you define your daemons that you don't define too many; each 
will be started as a separate process, so if you're running a lot of daemons,
they won't actually be running simultaneously.

Note that "all" is a reserved keyword, so you can't use it as a name for a
daemon.
