<p align="center">
<img src="https://raw.githubusercontent.com/BYUCamachoLab/pyrolab/master/docs/_static/images/pyrolab_logo.svg" width="40%" alt="PyroLab">
</p>

---

<p align="center">
<img alt="Development version" src="https://img.shields.io/badge/master-v0.3.2-informational">
<a href="https://pypi.python.org/pypi/pyrolab"><img alt="PyPI Version" src="https://img.shields.io/pypi/v/pyrolab.svg"></a>
<img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/pyrolab">
<a href="https://pyrolab.readthedocs.io/"><img alt="Documentation Status" src="https://readthedocs.org/projects/pyrolab/badge/?version=latest"></a>
<a href="https://pypi.python.org/pypi/pyrolab/"><img alt="License" src="https://img.shields.io/pypi/l/pyrolab.svg"></a>
<a href="https://github.com/BYUCamachoLab/pyrolab/commits/master"><img alt="Latest Commit" src="https://img.shields.io/github/last-commit/BYUCamachoLab/pyrolab.svg"></a>
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

**Note:** while the software says "OS Independent", some of the servers *are*
OS-specific. For example, ThorLabs DLL's only work on Windows. However, you could
use PyroLab to connect to those devices from any operating system.

## Installation

PyroLab is pip installable:

```
pip install pyrolab
```

PyroLab declares several "extras", depending on which instruments you need
to support:

```
pip install pyrolab[tsl550, oscope]
```

The full list of supported extras is:
- tsl550
- oscope
- arduino
- monitor

You can also clone the repository, navigate to the toplevel, and install in 
editable mode (make sure you have pip >= 21.1):

```
pip install -e .
```

## Web Monitor

There's a web application that can monitor your PyroLab nameserver and 
provide an easy-to-access status board. It's a Flask app that can be served
using a production grade server. Install it using pip:

```
pip install pyromonitor
```

To run:

```
pyromonitor up
```

## Example

### Local Instruments

Locally available instruments just import drivers without using any of the 
other features of PyroLab.

```
from pyrolab.drivers.lasers.tsl550 import TSL550

laser = TSL550("COM4")
laser.on()
laser.power_dBm(12)
laser.open_shutter()
laser.sweep_set_mode(continuous=True, twoway=True, trigger=False, const_freq_step=False)
```

### Remote Instruments

First, make sure all configurations on the nameserver computer, instrument 
server computer, and client are correct (with the proper keys, if configured, 
etc.).

Run a nameserver:

```python
from pyrolab.api import start_ns_loop
start_ns_loop()
```

Provide a service:

```python
from pyrolab.api import Daemon, locate_ns
from pyrolab.drivers.sample import SampleService

daemon = Daemon()
ns = locate_ns(host="localhost")
uri = daemon.register(SampleService)
ns.register("test.SampleService", uri)

try:
    daemon.requestLoop()
finally:
    ns.remove("test.SampleService")
```

Connect using a remote client:

```python
from pyrolab.api import locate_ns, Proxy

ns = locate_ns(host="localhost")
uri = ns.lookup("test.SampleService")

with Proxy(uri) as service:
    resp = service.echo("Hello, server!")
    print(type(resp), resp)
```

## Instrument Server Configuration

PyroLab stores information about instruments and servers when it closes. This
means that once PyroLab has been configured once, each time it is restarted,
it will remember and reload the previous configuration. Hence, once a server
is set up, unless the available instruments, nameserver, or other 
configurations change, PyroLab will automatically work when started, every 
time!

For an example of how a new PyroLab instrument server should be configured the
first time it's run, see ``examples/library-catalog/config.yaml``.

## FAQ's
1. **Another instrument library? What about all the others?**  
    In our experience, many of the other libraries are buggy or have difficulty
    with network connections. So, our approach was to rely on a well developed
    and time-tested framework (Pyro) instead of worrying about developing and
    supporting our own custom set of servers.

2. **Is this a standalone software that automatically supports all the advertised 
instruments?**  
    No; many of these instruments depend on other software already being
    installed. In particular, ThorLabs equipment depends on ThorLabs software
    already being installed on the computer connected to the physical hardware
    (but not on the remote computer!). As much as possible, though, we try to
    make the drivers standalone capable.

## For Developers

Since the passing of data is, by definition, between hosts and over IP, PyroLab
avoids the use of complex Python objects for return values that will be 
transmitted to remote machines. Since serialization is complicated, and
security is even harder, we resort to using only basic Python types when
interfacing with hardware (i.e., Python lists, ints, tuples, and not NumPy 
arrays, matplotlib plot objects, custom objects, etc.).

## Releasing

Make sure you have committed a changelog file under ``docs/changelog`` titled 
``<major>.<minor>.<patch>-changelog.md`` before bumping version. Also, the git
directory should be clean (no uncommitted changes).

To bump version prior to a release, run one of the following commands:

```
bumpversion major
bumpversion minor
bumpversion patch
```

This will automatically create a git tag in the repository with the 
corrresponding version number and commit the modified files (where version
numbers were updated). Pushing the tags (a manual process) to the remote will 
automatically create a new release. Releases are automatically published to 
PyPI and GitHub when git tags matching the "v*" pattern are created 
(e.g. "v0.3.2"), as bumpversion does.

After bumping version, you can view the tags on the local machine by running 
``git tag``. To push the tags to the remote server and trigger the release
workflow, you can run ``git push origin <tagname>``.

For code quality, please run isort and black before committing (note that the
latest release of isort may not work through VSCode's integrated terminal, and
it's safest to run it separately through another terminal).

## Building the Docs

Much of the API documentation is autogenerated from the source code. Gitignores
are in place to prevent you from committing autogenerated pages.

To build the docs, navigate to the ``docs/`` directory and run:

```
pip install -r requirements.txt
make html
```

## Building the Package

You can test the build and view the bundled artifacts using 
[build](https://pypi.org/project/build/). It's recommended you build locally
before pushing to PyPI. In particular, double check the included files and make
sure only the required files are there by modifying MANIFEST.in as necessary.
