# from multiprocessing import Lock
# from pyrolab.api import locate_ns, behavior, change_behavior
# from pyrolab.drivers.sample import SampleService
# from pyrolab.daemon import LockableDaemon


# daemon = LockableDaemon()
# ns = locate_ns(host="localhost")
# SS = LockableDaemon.prepare_class(SampleService)
# SS = SS.set_behavior(instance_mode="single")
# print(SS._pyroInstancing)
# import sys; sys.exit()
# # uri = daemon.register(SS)
# # ns.register("test.SampleService", uri, metadata={"You can put lists of strings here!"})
# ns.register("test.SampleService", daemon.register(SS), metadata={"You can put lists of strings here!"})
# ns.register("LockableDaemon", daemon.register(daemon))
# print("READY")
# try:
#     daemon.requestLoop()
# finally:
#     ns.remove("test.SampleService")