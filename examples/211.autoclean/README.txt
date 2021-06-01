This is a simple example to help you test the nameserver's autoclean feature.

For a typical setup:
    1. Some publicly visible server will host "nameserver.py". 
    2. Your local computer will connect run "demo.py".

To test these, 2 terminal tabs are desirable, with commands executed
in each in the following order:
    1. ``python nameserver.py``
    2. ``python -i demo.py``

Even though it may take several seconds longer for autoclean to work than one
might expect, continue running the commands as explained in ``demo.py`` to 
see the autoclean feature work.
