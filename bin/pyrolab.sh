#!/usr/bin/env bash

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

"""
Startup Script
==============

An example daemon autolaunch configuration for *nix machines.


First, configure PyroLab by running the following command:

    pyrolab config update <config-file>.yaml

Then, a file similar to this one will act as your startup script. 
Be sure to give it executable permissions before registering it with crontab:

    chmod +x pyrolab.sh

You'll want to register it with crontab by running:
    
        crontab -e
    
Then, add the following line to your crontab file:

    @reboot /path/to/pyrolab.sh

The rest of this script assumes you're using Anaconda (or miniconda) and
have a Python 3.7+ environment named 'pyrolab'.
"""

source ~/miniconda3/bin/activate
conda activate pyro
pyrolab up --force
