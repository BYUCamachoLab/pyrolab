import pyrolab

from pyrolab.nameserver import load_nameserver_configs, start_ns_loop

configs = load_nameserver_configs("config.yml")

print("Available configurations:", list(configs.keys()))

print(configs['default'])
start_ns_loop(configs["default"])
