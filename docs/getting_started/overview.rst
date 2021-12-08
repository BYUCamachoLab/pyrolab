========
Overview
========

Why another instrumentation library?
------------------------------------

There already exists several instrumentation libraries for Python. Like any
good developer, the original author sought after an existing library for his
particular use case and, upon finding his quest unproductive, created his own
from scratch: PyroLab.

.. figure:: https://www.explainxkcd.com/wiki/images/6/60/standards.png
   :width: 500
   :alt: Standards comic strip (XKCD)
   :target: https://xkcd.com/927/
   
   *Fortunately, the charging one has been solved now that we've all
   standardized on mini-USB. Or is it micro-USB? Shit.*
   (`xkcd <https://xkcd.com/927/>`_)

In this case, the specific issues that PyroLab was trying to solve were:

#. PyroLab was created within an academic institution environment, where:
#. All the computers we get from the computer support resource office are the 
   old and crappy leftovers from computing labs.
#. Every subgroup and setup has its own custom software for the same hardware,
   and it's not very transferrable.
#. Sometimes our drivers need to transfer large amounts of data.
#. The aforementioned old and crappy computers can't handle being connected
   to multiple hardware devices *and* acquire data simultaneously; they freeze,
   become bogged down, and are just a general pain to use.
#. We only have one of a specific hardware instrument, shared between multiple 
   setups that each have their own dedicated control computer, and we don't 
   want to keep moving the plug back and forth.

PyroLab attempts to solve this problem by:

#. Allowing local machines to host specific hardware devices that can be 
   accessed remotely by any number of machines.
#. Allowing remote machines to connect to any number of local machines, thereby
   aggregating data or control from multiple hardware devices to one computer.
#. Allowing a single Core i5 machine from 2012 to dedicate itself 
   wholeheartedly to running one particularly resource hungry hardware device
   without having to also deal with 4 other hardware devices.

In other words, PyroLab is both a distributed hardware device network manager 
**and** a one-stop repository for hardware drivers. It allows researchers (in 
our context, perhaps you will use this in other settings) to use a single 
language, Python, a very popular language for prototyping and scientific
computing, to control a whole variety of devices from a script-based approach.
In an academic research lab setting, it allows users to "bring your own 
computer" and access experiments and hardware hosted from any number of "host"
computers. No more cable management issues, no more arguing over "who has the
laser today," and no more issues with slow computers that can only manage
one frame per second from the microscope while running Windows 10.

Yes, it was written, tailored to our use case. But, we tried to keep it general
enough so that you, too, will find it so invaluable that you'll want to use it,
develop it, and contribute new drivers to it.

So, welcome to PyroLab. Read on, to learn about the philosophy of the framework
and how to use it properly.