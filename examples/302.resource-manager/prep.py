from pyrolab.server.configure import ServerConfiguration
from pyrolab.server.registry import InstrumentInfo, InstrumentRegistry
from pyrolab.server.resource import ResourceInfo
from pyrolab.server.resourcemanager import ResourceManager

# We'll store a few sample "instruments"
i1 = InstrumentInfo("test.SampleService", "pyrolab.drivers.sample", "SampleService", lockable=False)
i2 = InstrumentInfo("test.SampleAutoconnectInstrument", "pyrolab.drivers.sample", "SampleAutoconnectInstrument", {"address": "0.0.0.0", "port": 8080}, lockable=False)

# We'll use our own InstrumentRegistry to create the registry file.
ir = InstrumentRegistry()
ir.register(i1)
ir.register(i2)

# Write the registry file somewhere we can find it, then load it into PyroLab
REG_FILE = "./registry.yaml"
ir.save(REG_FILE)

from pyrolab.server.registry import registry
registry.load(REG_FILE)
registry.save()


# We'll now define the daemons that will host our known instruments. Be sure
# to use the same identifying string!
srv_cfg = ServerConfiguration(
    host="public",
    ns_host = "camacholab.ee.byu.edu",
)
r1 = ResourceInfo("test.SampleService", srv_cfg=srv_cfg, daemon_module="pyrolab.server", daemon_class="LockableDaemon")
r2 = ResourceInfo("test.SampleAutoconnectInstrument", srv_cfg=srv_cfg, daemon_module="pyrolab.server", daemon_class="AutoconnectLockableDaemon")

# We'll use our own ResourceManager to create the manager info file.
rm = ResourceManager()
rm.add(r1)
rm.add(r2)

# Write the info file somewhere we can find it, then load it into PyroLab
MAN_FILE = "./manager.yaml"
rm.save(MAN_FILE)

from pyrolab.server.resourcemanager import manager
manager.load(MAN_FILE)
manager.save()
