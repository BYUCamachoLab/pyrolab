# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Simphony Photonic Simulator.

This module implements a free and open source photonic integrated
circuit (PIC) simulation engine. It is speedy and easily extensible.
"""

import io
import sys

import setuptools

from pyrolab import __version__, __author__, __maintainer__, __maintainer_email__, __website_url__  # analysis:ignore

# ==============================================================================
# Constants
# ==============================================================================
NAME = "PyroLab"
LIBNAME = "pyrolab"

# ==============================================================================
# Auxiliary functions
# ==============================================================================
extra_files = []
extra_files += ["*.ini"]

# ==============================================================================
# Use README for long description
# ==============================================================================
with io.open("README.md", encoding="utf-8") as f:
    LONG_DESCRIPTION = f.read()

# ==============================================================================
# Setup arguments
# ==============================================================================
setup_args = dict(
    name=NAME,
    version=__version__,
    author="Sequoia Ploeg",
    maintainer=__maintainer__,
    maintainer_email=__maintainer_email__,
    url=__website_url__,
    description="A framework for using remote lab instruments as local resources built on Pyro5",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    # download_url=__website_url__ + "",
    license="GPLv3+",
    keywords="laboratory instrumentation hardware science remote network integration",
    platforms=["Windows", "Linux", "Mac OS-X"],
    packages=setuptools.find_packages(),
    package_data={"": extra_files},
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering",
    ],
    python_requires=">=3.6",
)

install_requires = [
    "Pyro5",
    "appdirs",
    "PyYAML",
]

extras_require = {
    # "kinesis": ["",],
    "ssl": ["cryptography",],
    "test": ["pytest",],
}

if "setuptools" in sys.modules:
    setup_args["install_requires"] = install_requires
    setup_args["extras_require"] = extras_require


# ==============================================================================
# Main setup
# ==============================================================================
setuptools.setup(**setup_args)
