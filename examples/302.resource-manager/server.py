# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Resource Manager
----------------

Resources are declared and written to a file in ``prep.py``. This scripts loads
that file into PyroLab's ``manager`` object and launches all resources.

Run this file with 

```python
python -i server.py
```

to continue interacting with the ``manager`` object, including calls like:

```
manager.AUTORELAUNCH = False
manager.shutdown_all()
```
"""

from pyrolab.server.resourcemanager import ResourceManager

MAN_FILE = "./manager.yaml"

# For Windows machines, all process creation must be guarded in
# __name__ == "__main__"
if __name__ == "__main__":
    manager = ResourceManager.instance()
    manager.load(MAN_FILE)
    manager.launch_all()
