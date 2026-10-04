# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

PyroLab exposes lab instruments (USB/serial/VISA-connected hardware) as remote objects over
[Pyro5](https://pyro5.readthedocs.io/). A driver class is registered with a Pyro daemon, published to a
nameserver by name, and a client connects with a `Proxy`. Drivers can be OS-specific (ThorLabs DLLs are
Windows-only) even though clients are not.

## Commands

```
make install        # pip install -e .[dev] + pre-commit install
make test           # coverage run -m pytest; coverage report
make format         # black pyrolab
make mypy           # mypy -p pyrolab
make doc            # jupyter-book build docs (jb build docs)
make serve          # serve docs/_build/html on localhost
make build          # rm -rf dist && python -m build
make precommit      # pre-commit run --all-files
```

Single test: `pytest tests/test_configure.py::test_name` (pytest config lives in `pyproject.toml`;
`testpaths = ["tests"]`, `--maxfail=2` — pass `--maxfail=0` to see every failure).

Run isort and black before committing (pre-commit runs black; note isort's pre-commit hook has a stale
`files: photonic_schemas/.*` filter, so it effectively never runs — invoke isort manually). CI checks only
black, pinned to 23.3.0 to match pre-commit.

## Testing

The suite needs no hardware, vendor SDKs, or network beyond loopback, and CI
(`.github/workflows/tests.yml`) runs it on every PR and push to `master`: black, then pytest on Ubuntu and
Windows for Python 3.11–3.14 (the versions upstream still supports).

- **Pyro tests use real sockets on localhost, in threads.** The `serve` fixture runs a daemon's request loop
  in a background thread and shuts it down afterwards. Nothing spawns child processes, so `ProcessManager`
  launch/shutdown/checkup are untested; `DaemonRunner.setup_daemon()` is exercised in-process instead.
- **`Pyro5.config` is reset around every test** (autouse `pyro_config` fixture), because
  `update_pyro_config()` writes Pyro5 process globals and importing `pyrolab.api` applies the developer's
  own user config. Still pass `host="localhost"` explicitly when constructing daemons.
- **Use the `data_dir` fixture for anything touching runtime files** (`USER_CONFIG_FILE`, `RUNTIME_CONFIG`,
  `LOCKFILE`, `PYROLAB_LOGDIR`, `NAMESERVER_STORAGE`). Tests must never write to the real data dir. See
  "Runtime state" for why patching `pyrolab.X` alone is not enough.
- `global_config` gives a fresh `GlobalConfiguration` singleton; `sample_config_yaml` / `sample_config_file`
  are a complete valid config using only `pyrolab.server` and `pyrolab.drivers.sample`.
- **Hardware tests** get `@pytest.mark.hardware` and are skipped unless `--run-hardware` is passed. Import
  vendor modules inside the test, not at module level, or collection fails on machines without the SDK.
- `test_imports.py` imports every module (skipping drivers whose optional dependency or SDK is missing) and
  compiles every source file with warnings as errors, so invalid escape sequences fail the suite.
- Regression tests cite their issue in a comment, e.g. `# Regression: ... (#45)`.

## Architecture

Three cooperating roles, each configurable independently and often on different machines:

- **Nameserver** — a Pyro nameserver, wrapped in `pyrolab/nameserver.py` so it reads PyroLab config and
  supports a loop-kill condition.
- **Daemon** (`pyrolab/server.py`) — `Daemon` subclasses `Pyro5.server.Daemon` and adds a `_prepare_class`
  hook applied on `register()`. `LockableDaemon` uses that hook to dynamically mix `Lockable` into the
  service class, giving clients exclusive locks (only valid for `instance_mode="single"`), auto-released on
  disconnect.
- **Service / Instrument** (`pyrolab/service.py`, `pyrolab/drivers/__init__.py`) — `Service` is the base for
  anything hosted; `Instrument` adds the hardware lifecycle.

### Configuration is the program

`pyrolab/configure.py` is the center of gravity. A single YAML file (pydantic v1 models) declares
`nameservers`, `daemons`, `services`, and `autolaunch` (see the `sample_config_yaml` fixture in
`tests/conftest.py` and `examples/library-catalog/config.yaml`; `tests/data/*.yaml` are stale and reference
a `pyrolab.daemon` module that no longer exists). A `ServiceConfiguration` names a `module` + `classname` that is
imported dynamically at launch; `_get_service()` then calls `uniquify_class()` to create a uniquely-named
subclass, sets the Pyro instance mode, and stashes `parameters` on `_autoconnect_params`. The uniquify step
exists because autoconnect parameters live as *class* attributes — two hardware units of the same model would
otherwise clobber each other.

`GlobalConfiguration` is a singleton and **must only be touched from the main process**. Child processes read
the frozen `RUNTIME_CONFIG` file instead, which is why config changes require `pyrolab reload` rather than
taking effect live.

### Process model

`pyrolab/pyrolabd.py` is the background daemon (`PyroLabDaemon`, `instance_mode="single"`), launched by
`pyrolab up`, which runs `pyrolabd.py` as a detached subprocess (`pythonw.exe` on Windows). It writes pid+URI to `LOCKFILE`, and the
CLI reaches it by reading that file. It owns a `ProcessManager` (`pyrolab/manager.py`) singleton that spawns
each nameserver and each daemon as its own `multiprocessing.Process` (`NameServerRunner`, `DaemonRunner`), so
a hung instrument kills only its own process. Runners are controlled by sentinel `None` on a
`multiprocessing.Queue`; `ProcessManager.checkup()` restarts dead ones on a timer.

Everything spawn-related lives in `manager.py` specifically because child processes re-import the target
module — keeping process creation out of that import path prevents recursive spawning.

### CLI

`pyrolab/cli.py` is a typer app (`pyrolab` entry point) with sub-apps: `up`/`down`/`reload`/`ps`/`info`,
`config update|reset|export`, `start|stop nameserver|daemon`, `rename`, `logs clean|export`, `nslist`.
Most commands are thin wrappers that proxy to the running `PyroLabDaemon`.

### Runtime state

`pyrolab/__init__.py` creates and exports the data-dir constants at import time: `PYROLAB_DATA_DIR`
(`pyrolab/data/local/` inside the package), `USER_CONFIG_FILE`, `RUNTIME_CONFIG`, `LOCKFILE`,
`NAMESERVER_STORAGE`, `PYROLAB_LOGDIR`. It also installs a rotating file handler writing to
`logs/pyrolab_<pid>.log`. Env vars: `PYROLAB_LOGLEVEL`, `PYROLAB_LOGFILE`, `PYROLAB_HUSH_DEPRECATION`.

Other modules bind these constants by value (`from pyrolab import LOCKFILE, ...` in `api`, `cli`,
`configure`, `manager`, `pyrolabd`), so redirecting a path means patching it in each of those modules —
which is what the `data_dir` test fixture does.

`pyrolab/api.py` is the intended public surface — it re-exports the Pyro5 names plus PyroLab's, and on import
applies the first configured nameserver's settings to `Pyro5.config` so `locate_ns()` just works. It is
excluded from isort (`extend_skip_glob = "api.py"`); import order there is load-bearing.

## Conventions

- **Return only basic Python types from exposed methods.** Anything crossing the wire must serialize under
  Pyro5's serializer — lists, ints, tuples, dicts; never NumPy arrays, matplotlib objects, or custom classes.
- **Instruments never connect in `__init__`.** Pyro instantiates hosted objects and keeps them alive, so
  `Instrument` subclasses implement `connect(**kwargs)` / `close()` / `detect_devices()` separately. All
  `connect()` arguments must be keyword arguments with defaults — `autoconnect()` dictionary-unpacks
  `_autoconnect_params` into it.
- numpydoc docstrings and type hints throughout; the API docs are autogenerated from them.
- Log via the `logging` module (`log = logging.getLogger(__name__)`). Servers run windowless in child
  processes and fail silently, so logs are often the only diagnostic.
- Optional hardware dependencies belong in a pyproject extra (`tsl550`, `ppcl55x`, `rto`, `arduino`), not in
  the base `dependencies`. PyPI rejects direct git URLs, so git-sourced extras stay commented out.
- Pinned to **pydantic 1.x** (`BaseSettings`, `validator`, `PrivateAttr` from `pydantic.fields`). Do not
  migrate to pydantic 2 piecemeal.

## Releasing

Commit `docs/changelog/<major>.<minor>.<patch>-changelog.md` first and ensure a clean tree — the release
workflow reads that exact file as the GitHub release body and fails without it. Then `make release-patch`
(or `-minor`/`-major`), which runs bump2version (updating `pyrolab/__init__.py`, `README.md`,
`pyproject.toml`), commits, tags `vX.Y.Z`, and pushes. The `v*` tag triggers
`.github/workflows/release.yml`, which first runs the full test workflow and only then builds, publishes to
PyPI, and creates the GitHub release.
