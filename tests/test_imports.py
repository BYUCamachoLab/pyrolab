"""
Import every module in the package.

Core modules must always import. Driver modules may legitimately fail when an
optional dependency or vendor SDK (pyserial, pyvisa, ThorLabs Kinesis, ...) is
not installed; those are skipped. Any other failure -- a syntax error, a
NameError at module scope, a broken import of another ``pyrolab`` module --
fails the test.
"""

import importlib
import pathlib
import pkgutil
import warnings

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


PACKAGE_DIR = pathlib.Path(pyrolab.__file__).parent
SOURCE_FILES = sorted(PACKAGE_DIR.rglob("*.py"))


@pytest.mark.parametrize(
    "path", SOURCE_FILES, ids=lambda p: p.relative_to(PACKAGE_DIR).as_posix()
)
def test_source_compiles_without_warnings(path):
    # Compiling directly (rather than importing) checks every file, including
    # drivers whose dependencies are missing, and isn't masked by cached .pyc
    # files. Invalid escape sequences warn today and become errors in a future
    # Python release.
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        compile(path.read_text(encoding="utf-8"), str(path), "exec")


@pytest.mark.parametrize(
    "contents",
    [
        "autolaunch: {daemons: [ghost]}\n",  # fails validation
        "nameservers: {\n",  # not valid YAML
        "daemons: {d: {}}\n",  # valid, but no nameservers
    ],
)
def test_api_import_survives_any_user_config(data_dir, contents):
    # Regression: importing pyrolab.api loaded the user config strictly, so an
    # invalid one (or one with no nameservers) broke every client script and
    # every CLI command, including the ones that would fix it.
    import pyrolab.api

    data_dir.USER_CONFIG_FILE.write_text(contents)
    importlib.reload(pyrolab.api)


def test_api_import_applies_first_nameserver(data_dir, pyro_config):
    import pyrolab.api

    data_dir.USER_CONFIG_FILE.write_text(
        "nameservers:\n  first: {host: 127.0.0.1, ns_port: 9555}\n"
        "  second: {ns_port: 9666}\n"
    )
    importlib.reload(pyrolab.api)
    assert pyro_config.NS_PORT == 9555
