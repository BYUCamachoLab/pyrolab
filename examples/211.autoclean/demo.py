# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Autoclean
---------

If you run this file with the command

```python 
python -i demo.py
```

you will enter it in "interative" mode, which keeps around the local variables
so that you can continue manipulating them.

The nameserver has the AUTOCLEAN set to 1.0, but this doesn't deterministically
mean the server will autoclean every 1 second, but "around" that frequently
("around" is being generous).

If you wait several seconds, you'll eventually notice that if you continue
executing

```
print(c.list())
```

that the dead service will eventually be removed.
"""

from pyrolab.api import locate_ns
from pyrolab.drivers.sample import SampleService
from pyrolab.server import Daemon, srv_profile, DaemonConfiguration

#
# Server setup
#
cfg = DaemonConfiguration(servertype="multiplex")
srv_profile.use(cfg)

daemon = Daemon()
ns = locate_ns(host="localhost")
uri = daemon.register(SampleService)
ns.register("test.SampleService", uri)

print("SERVER REGISTERED AND CLOSING")

#
# Client/Proxy side
#
c = Client()
print(c.list())
