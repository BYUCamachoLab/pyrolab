# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

import socket
import secrets
import pkg_resources


def get_ip() -> str:
    """
    Get the IP address of the local machine.

    Returns
    -------
    str
        The IP address of the local machine.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def generate_random_name(count: int=3) -> str:
    """
    Concatenates ``count`` random words as a hyphenated string.

    Wordlist is located in pyrolab/data/wordlist.txt.

    Parameters
    ----------
    count : int, optional
        How many words to use in the hyphenated string.

    Returns
    -------
    str
        A hyphenated string of ``count`` random words.
    """
    import random
    from pathlib import Path

    path = Path(pkg_resources.resource_filename('pyrolab', "data/wordlist.txt"))
    with open(path, 'r') as f:
        wordlist = f.read().splitlines()

    return '-'.join([secrets.choice(wordlist) for _ in range(count)])
