"""
Shared fixtures for the PyroLab test suite.

Nothing here needs lab hardware, vendor SDKs, or a network beyond loopback.
"""

import threading
import time
from types import SimpleNamespace

import Pyro5
import pytest

from pyrolab.configure import GlobalConfiguration


def pytest_addoption(parser):
    parser.addoption(
        "--run-hardware",
        action="store_true",
        default=False,
        help="Run tests marked 'hardware', which need physical lab instruments.",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-hardware"):
        return
    skip = pytest.mark.skip(reason="needs lab hardware (use --run-hardware)")
    for item in items:
        if "hardware" in item.keywords:
            item.add_marker(skip)


# Modules that bind the data-dir constants at import time with
# ``from pyrolab import ...``. Each needs patching individually, since
# rebinding ``pyrolab.LOCKFILE`` alone does not affect their copies.
_DATA_PATH_MODULES = [
    "pyrolab",
    "pyrolab.api",
    "pyrolab.cli",
    "pyrolab.configure",
    "pyrolab.manager",
    "pyrolab.pyrolabd",
]


@pytest.fixture(autouse=True)
def pyro_config():
    """
    Isolate each test from Pyro5's process-global configuration.

    ``update_pyro_config()`` writes straight to ``Pyro5.config``, and importing
    ``pyrolab.api`` applies the developer's own user configuration to it, so
    without this the results of one test (or of the local machine's setup)
    leak into the next.
    """
    saved = Pyro5.config.as_dict()
    Pyro5.config.reset(use_environment=False)
    yield Pyro5.config
    for key, value in saved.items():
        setattr(Pyro5.config, key, value)


@pytest.fixture(autouse=True)
def no_version_check(monkeypatch):
    """
    Keep CLI tests off the network: every CLI command checks PyPI for updates
    unless this variable is set. Tests of the check itself delete it.
    """
    monkeypatch.setenv("PYROLAB_NO_VERSION_CHECK", "1")


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    """
    Redirect PyroLab's files (configs, lockfile, logs, ...) into a temp dir.

    Autouse, so no test can touch the real per-user directories (or copy files
    from a developer's real pre-0.5 install). Returns a namespace with the
    redirected paths; only the log and nameserver directories exist up front.
    """
    root = tmp_path / "pyrolab-data"
    paths = SimpleNamespace(
        root=root,
        USER_CONFIG_FILE=root / "user_configuration.yaml",
        RUNTIME_CONFIG=root / "runtime_config.yaml",
        LOCKFILE=root / "pyrolabd.lock",
        UPDATE_CHECK_FILE=root / "update_check.json",
        STARTUP_ERROR_FILE=root / "pyrolabd_startup_error.txt",
        PYROLAB_LOGDIR=root / "logs",
        PYROLAB_LOGFILE=root / "logs" / "pyrolab.log",
        NAMESERVER_STORAGE=root / "nameserver",
        LEGACY_DATA_DIR=root / "legacy",  # absent unless a test creates it
        LEGACY_MIGRATION_MARKER=root / "legacy_files_copied.txt",
    )
    paths.PYROLAB_LOGDIR.mkdir(parents=True)
    paths.NAMESERVER_STORAGE.mkdir()

    import importlib

    for modname in _DATA_PATH_MODULES:
        module = importlib.import_module(modname)
        for attr, value in vars(paths).items():
            if attr != "root" and hasattr(module, attr):
                monkeypatch.setattr(module, attr, value)
    return paths


@pytest.fixture
def global_config():
    """
    A fresh ``GlobalConfiguration`` singleton, discarded after the test.
    """
    GlobalConfiguration._instance = None
    yield GlobalConfiguration.instance()
    GlobalConfiguration._instance = None


@pytest.fixture
def serve():
    """
    Factory that runs a Pyro daemon's request loop in a background thread.

    Every daemon passed in is shut down and joined at teardown.
    """
    running = []

    def _serve(daemon):
        thread = threading.Thread(target=daemon.requestLoop, daemon=True)
        thread.start()
        running.append((daemon, thread))
        return daemon

    yield _serve

    for daemon, thread in running:
        daemon.shutdown()
        thread.join(timeout=5)
        daemon.close()


@pytest.fixture
def wait_for():
    """
    Returns a function that polls ``condition`` until it returns truthy or
    ``timeout`` seconds pass, then returns the final result of ``condition()``.
    """

    def _wait_for(condition, timeout=5.0, interval=0.01):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = condition()
            if result:
                return result
            time.sleep(interval)
        return condition()

    return _wait_for


@pytest.fixture
def sample_config_yaml():
    """
    A complete, valid configuration that refers only to importable modules.
    """
    return """\
version: '1.0'
nameservers:
  local:
    host: localhost
    ns_port: 9090
  persistent:
    host: localhost
    ns_port: 9100
    storage: sql
daemons:
  plain:
    host: localhost
  lockable:
    classname: LockableDaemon
    servertype: multiplex
    nameservers:
    - local
services:
  sample.echo:
    module: pyrolab.drivers.sample
    classname: SampleService
    description: Echo service
    daemon: plain
    nameservers:
    - local
  sample.instrument:
    module: pyrolab.drivers.sample
    classname: SampleAutoconnectInstrument
    parameters:
      address: 0.0.0.0
      port: 1234
    instancemode: single
    daemon: lockable
autolaunch:
  nameservers:
  - local
  daemons:
  - lockable
"""


@pytest.fixture
def sample_config_file(tmp_path, sample_config_yaml):
    path = tmp_path / "config.yaml"
    path.write_text(sample_config_yaml)
    return path
