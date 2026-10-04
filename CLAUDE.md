# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

PyroLab exposes lab instruments (USB/serial/VISA-connected hardware) as remote objects over
[Pyro5](https://pyro5.readthedocs.io/). A driver class is registered with a Pyro daemon, published to a
nameserver by name, and a client connects with a `Proxy`. Drivers can be OS-specific (ThorLabs DLLs are
Windows-only) even though clients are not.

## Commands

```
make install        # uv sync --all-extras + pre-commit install
make test           # uv run coverage run -m pytest; coverage report
make format         # ruff check --fix (import sorting) + ruff format
make mypy           # mypy -p pyrolab
make doc            # jupyter-book build docs (uses the "docs" dependency group)
make serve          # serve docs/_build/html on localhost
make build          # rm -rf dist && uv build
make precommit      # pre-commit run --all-files (what CI's lint job runs)
```

The project is managed with **uv**: `uv.lock` is committed, and the dev tools live in `[dependency-groups]`
(`dev`, installed by default; `docs`), not in published extras. Run tools through `uv run`. After changing
dependencies in `pyproject.toml`, run `uv lock` — CI uses `uv sync --locked` and fails on a stale lock.

Single test: `uv run pytest tests/test_configure.py::test_name` (pytest config lives in `pyproject.toml`;
`testpaths = ["tests"]`, `--maxfail=2` — pass `--maxfail=0` to see every failure).

Formatting and import sorting are **ruff** (`[tool.ruff]` in `pyproject.toml`), enforced by pre-commit and
by CI. Only the isort rules (`I`) are enabled for linting so far. The ruff version is pinned in two places
that must stay in step: `.pre-commit-config.yaml` and the `dev` group in `pyproject.toml`.

## Testing

The suite needs no hardware, vendor SDKs, or network beyond loopback, and CI
(`.github/workflows/tests.yml`) runs it on every PR and push to `master`: pre-commit on every file, then
pytest on Ubuntu and Windows for Python 3.11–3.14 (the versions upstream still supports) with every extra
installed, so all drivers whose dependencies are on PyPI get import-tested.

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
`logs/pyrolab_<pid>.log`. Env vars: `PYROLAB_LOGLEVEL`, `PYROLAB_LOGFILE`, `PYROLAB_HUSH_DEPRECATION`,
`PYROLAB_NO_VERSION_CHECK`.

**Importing `pyrolab` must never touch the network.** The PyPI update check lives in `pyrolab/updates.py`
and runs only from the CLI's main callback, at most once a day (result cached in `UPDATE_CHECK_FILE`).
An autouse test fixture sets `PYROLAB_NO_VERSION_CHECK` so CLI tests stay offline, and
`test_updates.py` fails if importing the package performs any hostname lookup.

Other modules bind these constants by value (`from pyrolab import LOCKFILE, ...` in `api`, `cli`,
`configure`, `manager`, `pyrolabd`), so redirecting a path means patching it in each of those modules —
which is what the `data_dir` test fixture does.

`pyrolab/api.py` is the intended public surface — it re-exports the Pyro5 names plus PyroLab's, and on import
applies the first configured nameserver's settings to `Pyro5.config` so `locate_ns()` just works. It is
excluded from import sorting (a ruff per-file ignore); import order there is load-bearing.

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
- Optional hardware dependencies belong in a pyproject extra (`tsl550`, `ppcl55x`, `rto`, `arduino`,
  `cameras`), not in the base `dependencies`. PyPI rejects direct git URLs, so git-sourced extras stay
  commented out. `[tool.uv.sources]` can point development installs at git, but PyPI users never see it, so
  don't rely on it to fix a broken release — the Arduino driver patches PyPI's pyfirmata 1.1.0 instead.
- Pinned to **pydantic 1.x** (`BaseSettings`, `validator`, `PrivateAttr` from `pydantic.fields`). Do not
  migrate to pydantic 2 piecemeal.

## Releasing

The version lives only in `pyproject.toml`; `pyrolab.__version__` reads it from installed package metadata
(`importlib.metadata`), so never hard-code it elsewhere.

Commit `docs/changelog/<major>.<minor>.<patch>-changelog.md` first and ensure a clean tree — the release
workflow reads that exact file as the GitHub release body and fails without it. Then `make release-patch`
(or `-minor`/`-major`), which checks both of those, runs `uv version --bump`, commits `pyproject.toml` and
`uv.lock`, tags `vX.Y.Z`, and pushes. The `v*` tag triggers `.github/workflows/release.yml`: the full test
workflow, then a build job (tag must match the `pyproject.toml` version, changelog must exist,
`uv build --no-sources`, `twine check --strict`), then publishing via PyPI **Trusted Publishing** (OIDC from
the `pypi` environment — there is no PyPI token secret), then `gh release create --notes-file` with the
changelog. Renaming `release.yml` or the `pypi` environment breaks publishing until the trusted publisher on
pypi.org is updated to match. PRs that touch `release.yml`, and manual `workflow_dispatch` runs, are dry runs:
build and checks only, nothing published.
