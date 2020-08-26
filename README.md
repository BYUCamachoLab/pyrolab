<p align="center">
<img src="https://raw.githubusercontent.com/sequoiap/pyrolab/master/docs/source/_static/images/pyrolab_logo.svg" width="40%" alt="PyroLab">
</p>

---

<p align="center">
<img alt="Development version" src="https://img.shields.io/badge/master-v0.1.0-informational">
<!-- <a href="https://pypi.python.org/pypi/pyrolab"><img alt="PyPI Version" src="https://img.shields.io/pypi/v/pyrolab.svg"></a> -->
<!-- <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/pyrolab"> -->
<!-- <a href="https://github.com/BYUCamachoLab/simphony/actions?query=workflow%3A%22build+%28pip%29%22"><img alt="Build Status" src="https://github.com/BYUCamachoLab/simphony/workflows/build%20(pip)/badge.svg"></a> -->
<!-- <a href="https://github.com/pre-commit/pre-commit"><img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white" alt="pre-commit" style="max-width:100%;"></a> -->
<!-- <a href="https://simphonyphotonics.readthedocs.io/"><img alt="Documentation Status" src="https://readthedocs.org/projects/simphonyphotonics/badge/?version=latest"></a> -->
<!-- <a href="https://pypi.python.org/pypi/pyrolab/"><img alt="License" src="https://img.shields.io/pypi/l/pyrolab.svg"></a> -->
<a href="https://github.com/sequoiap/pyrolab/commits/master"><img alt="Latest Commit" src="https://img.shields.io/github/last-commit/sequoiap/pyrolab.svg"></a>
</p>

A framework for using remote lab instruments as local resources, built on Pyro5.

Developed by Sequoia Ploeg (for [CamachoLab](https://camacholab.byu.edu/), 
Brigham Young University).

## About
This project aims to allow all laboratory instruments to be accessed as
local objects from a remote machine. Instruments that don't natively
support such access, such as those required to be connected by a USB cable
(or similar), are wrapped with a Pyro5 interface. However, this library may
contain other instruments that are already internet-capable and don't rely
on Pyro5. That's alright; we're just trying to create a minimal-dependency,
one-stop-shop for laboratory instruments!

## Example

First, make sure all your configuration files on the nameserver computer, service
providing computer, and client are correct (with the proper keys and everything).

Run a nameserver:

```python
import pyrolab.api
pyrolab.api.config.reset(use_file="/path/to/config.yaml")

pyrolab.api.start_ns_loop()
```

Provide a service:

```python
import pyrolab.api
from pyrolab.drivers.sample import SampleService
pyrolab.api.config.reset(use_file="/path/to/config.yaml")

daemon = pyrolab.api.Daemon()
ns = pyrolab.api.locate_ns()
uri = daemon.register(SampleService)
ns.register("test.SampleService", uri)

try:
    daemon.requestLoop()
finally:
    ns.remove("test.SampleService")
```

Connect using a remote client:

```python
from pyrolab.api import config, locate_ns, Proxy
config.reset(use_file="/path/to/config.yaml")

ns = pyrolab.api.locate_ns()
uri = ns.lookup("test.SampleService")

with Proxy(uri) as p:
    p.do_work()
```

## FAQ's
1. **Another instrument library? What about all the others?**  
    In our experience, etc.

2. **Is this a standalone software that automatically supports all the advertised 
instruments?**  
    No; many of these instruments depend on other software already being
    installed. In particular, ThorLabs equipment depends on ThorLabs software
    already being installed on the computer connected to the physical hardware
    (but not on the remote computer!).

## For Developers
Since the passing of data is, by definition, between hosts and over IP, PyroLab
avoids the use of complex Python objects for return values that will be 
transmitted to remote machines. Since serialization is complicated, and
security is even harder, we resort to using only basic Python types when
interfacing with hardware (i.e., Python lists, ints, tuples, and not NumPy 
arrays, matplotlib plot objects, custom objects, etc.).

To bump version prior to a release, run one of the following commands:

```bash
bump2version major
bump2version minor
bump2version patch
```

Releases are automatically created when git tags matching the "v*" pattern
are created.
