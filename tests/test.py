import pyrolab

from pyrolab.nameserver import load_ns_configs, start_ns_loop

configs = load_ns_configs("config.yml")

print("Available configurations:", list(configs.keys()))

print(configs['default'])
start_ns_loop(configs["default"])
