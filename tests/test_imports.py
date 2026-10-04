"""
Import every module in the package.

Core modules must always import. Driver modules may legitimately fail when an
optional dependency or vendor SDK (pyserial, pyvisa, ThorLabs Kinesis, ...) is
not installed; those are skipped. Any other failure -- a syntax error, a
NameError at module scope, a broken import of another ``pyrolab`` module --
fails the test.
"""

import importlib
import pkgutil

import pytest

import pyrolab

CORE_MODULES = [
    "pyrolab",
    "pyrolab.api",
    "pyrolab.cli",
    "pyrolab.configure",
    "pyrolab.drivers",
    "pyrolab.drivers.sample",
    "pyrolab.manager",
    "pyrolab.nameserver",
    "pyrolab.pyrolabd",
    "pyrolab.server",
    "pyrolab.service",
    "pyrolab.utils",
]

ALL_MODULES = sorted(
    m.name
    for m in pkgutil.walk_packages(pyrolab.__path__, "pyrolab.")
    if m.name not in CORE_MODULES
)


@pytest.mark.parametrize("name", CORE_MODULES)
def test_core_module_imports(name):
    importlib.import_module(name)


@pytest.mark.parametrize("name", ALL_MODULES)
def test_driver_module_imports(name):
    try:
        importlib.import_module(name)
    except ImportError as e:
        # A missing pyrolab module is a real bug; anything else is an
        # optional dependency or vendor SDK that isn't installed here.
        if e.name and e.name.split(".")[0] == "pyrolab":
            raise
        pytest.skip(f"optional dependency unavailable: {e}")


def test_api_exports_resolve():
    import pyrolab.api as api

    for name in api.__all__:
        assert hasattr(api, name), name
