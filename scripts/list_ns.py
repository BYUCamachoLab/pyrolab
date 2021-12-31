#!/usr/bin/env python3

from tabulate import tabulate
from pyrolab.configure import NameServerConfiguration
from pyrolab.api import locate_ns


HOST = "localhost"
PORT = 9090

ns = locate_ns(host=HOST, port=PORT)
services = ns.list(return_metadata=True)

listing = []
for k, v in services.items():
    name = k
    uri, description = v
    listing.append([name, uri, ': '.join(description)])

print(tabulate(listing, headers=['NAME', 'URI', 'DESCRIPTION']))
