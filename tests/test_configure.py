# from pathlib import Path
# from pyrolab.configure import DaemonConfiguration, NameServerConfiguration, PyroLabConfiguration, ServiceConfiguration

# prod = PyroLabConfiguration(
#     nameservers={
#         "default": NameServerConfiguration(
#             host="public",
#             ns_port=9090,
#         ),
#         "production": NameServerConfiguration(
#             host="camacholab.ee.byu.edu",
#             ns_autoclean=15.0,
#             storage="sql",
#         ),
#         "development": NameServerConfiguration(
#             host="remotehost",
#             ns_port=9090,
#         ),
#     },
#     daemons={
#         "default": DaemonConfiguration(
#             classname="Daemon",
#             host="localhost",
#             servertype="thread",
#         ),
#         "lockable": DaemonConfiguration(
#             classname="LockableDaemon",
#             host="public",
#             servertype="thread",
#         ),
#         "multiplexed": DaemonConfiguration(
#             host="public",
#             servertype="multiplex",
#         ),
#     },
#     services={
#         "asgard.wolverine": ServiceConfiguration(
#             module="pyrolab.drivers.motion.z825b",
#             classname="PRM1Z8",
#             parameters={
#                 "serialno": 27003366,
#             },
#             description="Rotational motion",
#             instancemode="single",
#             daemon="lockable",
#             nameservers=["production",],
#         ),
#         "asgard.hulk": ServiceConfiguration(
#             module="pyrolab.drivers.motion.z825b",
#             classname="Z825B",
#             parameters={
#                 "serialno": 27003497,
#             },
#             description="Longitudinal motion",
#             instancemode="single",
#             daemon="lockable",
#             nameservers=["production",],
#         ),
#         "asgard.captainamerica": ServiceConfiguration(
#             module="pyrolab.drivers.motion.z825b",
#             classname="Z825B",
#             parameters={
#                 "serialno": 27504851,
#             },
#             description="Lateral motion",
#             instancemode="single",
#             daemon="lockable",
#             nameservers=["production",],
#         ),
#     }
# )

# dev = PyroLabConfiguration(
#     nameservers={
#         "default": NameServerConfiguration(
#             host="localhost",
#             ns_port=9090,
#         ),
#         "production": NameServerConfiguration(
#             host="public",
#             ns_port=9100,
#         ),
#     },
#     daemons={
#         "lockable": DaemonConfiguration(
#             classname="LockableDaemon",
#             host="public",
#             servertype="thread",
#         ),
#         "localthread": DaemonConfiguration(
#             classname="Daemon",
#             host="localhost",
#             servertype="thread",
#         ),
#     },
#     services={
#         "a": ServiceConfiguration(
#             module="pyrolab.drivers.sample",
#             classname="SampleService",
#             description="Lockable sample service",
#             instancemode="single",
#             daemon="lockable",
#             nameservers=["default",],
#         ),
#         "b": ServiceConfiguration(
#             module="pyrolab.drivers.sample",
#             classname="SampleAutoconnectInstrument",
#             parameters={
#                 "address": "0.0.0.0",
#                 "port": 9091,
#             },
#             description="Parameterized sample instrument",
#             instancemode="single",
#             daemon="lockable",
#             nameservers=["default",],
#         ),
#         "c": ServiceConfiguration(
#             module="pyrolab.drivers.sample",
#             classname="SampleService",
#             description="Not lockable sample service",
#             instancemode="single",
#             daemon="localthread",
#             nameservers=["default",],
#         ),
#     }
# )

# # data = plc.yaml()
# # print(data)

# tempprod = Path("./config.yaml")
# tempdev = Path("./devconfig.yaml")

# # with tempfile.open("w") as f:
# #     f.write(dev.yaml())

# plcprod = PyroLabConfiguration.from_file(tempprod)
# plcdev = PyroLabConfiguration.from_file(tempdev)

# # print(plcprod.yaml())
# # print(plcdev.yaml())


# from pyrolab.configure import PyroLabConfiguration
# from pyrolab import USER_CONFIG_FILE

# p1 = PyroLabConfiguration.from_file(USER_CONFIG_FILE)
# p2 = PyroLabConfiguration.from_file(USER_CONFIG_FILE)

# p1 == p2
