This is a simple example to help you test your configuration files
and server setup.

While PyroLab provides the framework and a set of drivers for using
instruments remotely, they should still each be started from their 
own script outside of the program files. Use PyroLab objects, but 
don't start instruments from within PyroLab--import them, and use
them as shown in this example.


For a typical setup:
    1. Some publicly visible server will host "nameserver.py". 
    2. The instrument connected to a computer will run "server.py".
    3. Your local computer will connect to remote resources as
       demonstrated in "client.py".

To test these, 4 terminal tabs are desirable, with commands executed
in each in the following order:
    1. ``python nameserver.py``
    2. ``python server.py``
    3. ``python client.py``
    4. python -m Pyro5.nsc -n localhost list

The last command will show the available Pyro objects. ``server.py``
has some code that cleans up its entry with the nameserver when the 
daemon is shut down, so running command 4 from above again will no
longer show the shut down objects in the list.