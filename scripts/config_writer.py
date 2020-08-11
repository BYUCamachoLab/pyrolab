# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
config_writer.py
----------------

Writes the example configuration file found in the /data directory.
"""

import configparser
from pathlib import Path

import pyrolab

datadir = Path(Path(pyrolab.__file__).parent, 'data')

config = configparser.ConfigParser()

config['DEFAULT'] = {
    'HOST': 'localhost',
    'NS_HOST': 'localhost',
    'SERVER_SSL_CERT_PATH': '',
    'CLIENT_SSL_CERT_PATH': '',
}

config['AVAILABLE_INSTRUMENTS'] = {

}


if __name__ == "__main__":
    print(datadir)