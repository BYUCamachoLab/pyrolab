#!/usr/bin/env python3

# Copyright © 2020- PyroLab Project Contributors and others (see AUTHORS.txt).
# The resources, libraries, and some source files under other terms (see NOTICE.txt).
#
# This file is part of PyroLab.
#
# PyroLab is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyroLab is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyroLab. If not, see <https://www.gnu.org/licenses/>.


from tabulate import tabulate
from pyrolab.api import locate_ns


HOST = "localhost"
PORT = 9090

ns = locate_ns(host=HOST, port=PORT)
services = ns.list(return_metadata=True)

listing = []
for k, v in services.items():
    name = k
    uri, description = v
    listing.append([name, uri, ": ".join(description)])

print(tabulate(listing, headers=["NAME", "URI", "DESCRIPTION"]))
