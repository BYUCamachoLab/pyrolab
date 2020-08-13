This is a simple example to help you test your configuration files
and server setup.

While PyroLab provides the framework and a set of drivers for using
instruments remotely, they should still each be started from their 
own script outside of the program files. Use PyroLab objects, but 
don't start instruments from within PyroLab--import them, and use
them as shown in this example.