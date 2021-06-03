
from pyrolab.server.registry import (
    InstrumentInfo, InstrumentRegistry, registry
)

# We'll store a few sample "instruments"
i1 = InstrumentInfo("test.SampleService", "pyrolab.drivers.sample", "SampleService", lockable=False)
i2 = InstrumentInfo("test.SampleAutoconnectInstrument", "pyrolab.drivers.sample", "SampleAutoconnectInstrument", {"address": "0.0.0.0", "port": 8080}, lockable=False)

# We'll use our own InstrumentRegistry to create the registry file.
ir = InstrumentRegistry()
ir.register(i1)
ir.register(i2)

REG_FILE = "./registry.yaml"
ir.save(REG_FILE)

# Now we'll load the registry into the global registry and see if it loads
# properly
registry.load(REG_FILE)
