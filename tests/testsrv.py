from pyrolab.api import locate_ns, behavior, change_behavior
from pyrolab.drivers.sample import SampleService
from pyrolab.server import LockableDaemon, create_lockable


daemon = LockableDaemon()
ns = locate_ns(host="localhost")
SS = create_lockable(SampleService)
SS = change_behavior(SS, instance_mode="single")
print(SS._pyroInstancing)
import sys; sys.exit()
# SS._pyroInstancing = ("single", None)
# uri = daemon.register(SS)
# ns.register("test.SampleService", uri, metadata={"You can put lists of strings here!"})
ns.register("test.SampleService", daemon.register(SS), metadata={"You can put lists of strings here!"})
ns.register("LockableDaemon", daemon.register(daemon))
print("READY")
try:
    daemon.requestLoop()
finally:
    ns.remove("test.SampleService")