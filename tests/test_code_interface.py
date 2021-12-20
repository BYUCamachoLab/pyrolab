import time

from pyrolab.manager import ProcessManager
from pyrolab.api import locate_ns, Proxy, GlobalConfiguration

GLOBAL_CONFIG = GlobalConfiguration.instance()
GLOBAL_CONFIG.load_config("tests/devconfig.yaml")
ns_names = list(GLOBAL_CONFIG.get_config().nameservers.keys())
pm = ProcessManager.instance()
print("nameservers:", ns_names)

pm.launch_nameserver('default')
pm.launch_daemon('lockable')

time.sleep(5)

ns = locate_ns()
services = list(ns.list().keys())[1:]

p1 = Proxy(ns.lookup(services[0]))
resp = p1.echo("hi there")
assert resp == "SERVER RECEIVED: hi there"

p2 = Proxy(ns.lookup(services[1]))
resp = p2.autoconnect()
assert resp == True

pm.shutdown_daemon('lockable')
pm.shutdown_nameserver('default')
