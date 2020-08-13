# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
appdirs
-------

Command line interface for PyroLab.
"""

import pyrolab.appdirs


def main(args=None):
    from argparse import ArgumentParser
    parser = ArgumentParser(description="PyroLab installation directory command line utility.")
    parser.add_argument("--user-data", action='store_true', help="show the path to the user data directory")
    parser.add_argument("--user-config", action='store_true', help="show the path to the user configuration file directory")
    parser.add_argument("--user-cache", action='store_true', help="show the path to the user cache directory")
    parser.add_argument("--site-data", action='store_true', help="show the path to the site data directory")
    parser.add_argument("--site-config", action='store_true', help="show the path to the site configuration file directory")
    parser.add_argument("--user-log", action='store_true', help="show the path to the user log directory")

    args = parser.parse_args()
    if args.user_data:
        print("user data:", pyrolab.appdirs.user_data_dir)
    if args.user_config:
        print("user config:", pyrolab.appdirs.user_config_dir)
    if args.user_cache:
        print("user cache:", pyrolab.appdirs.user_cache_dir)
    if args.site_data:
        print("site data:", pyrolab.appdirs.site_data_dir)
    if args.site_config:
        print("site config:", pyrolab.appdirs.site_config_dir)
    if args.user_log:
        print("user log:", pyrolab.appdirs.user_log_dir)


if __name__ == "__main__":
    main()
