"""
Where PyroLab keeps its files (#66), and what importing it changes (#63).
"""

import os
import subprocess
import sys
import textwrap

from pyrolab import locations

###############################################################################
# Layout
###############################################################################


def test_default_locations_are_per_user_and_named_once():
    locs = locations.locations({})
    for path in locs:
        assert "pyrolab" in path.parts
        assert path.parts.count("pyrolab") == 1  # no "pyrolab/pyrolab"
    # Not inside the installed package any more.
    package = locations.LEGACY_DATA_DIR.parent.parent
    assert all(package not in path.parents for path in locs)


def test_data_dir_override_puts_everything_in_one_place(tmp_path):
    locs = locations.locations({"PYROLAB_DATA_DIR": str(tmp_path)})
    assert locs.config_dir == locs.state_dir == locs.data_dir == tmp_path
    assert locs.cache_dir == tmp_path
    assert locs.log_dir == tmp_path / "logs"


###############################################################################
# Migration from a pre-0.5 install
###############################################################################


def legacy_install(root):
    legacy = root / "legacy"
    (legacy / "nameserver").mkdir(parents=True)
    (legacy / "user_configuration.yaml").write_text("daemons: {old: {}}\n")
    (legacy / "nameserver" / "ns_prod.sql").write_text("db")
    (legacy / "runtime_config.yaml").write_text("not copied")
    (legacy / "logs").mkdir()
    return legacy


def migrate(root, legacy):
    return locations.migrate_legacy_files(
        legacy,
        root / "config" / "user_configuration.yaml",
        root / "data" / "nameserver",
        root / "state" / "marker.txt",
    )


def test_migration_copies_config_and_nameserver_data(tmp_path):
    legacy = legacy_install(tmp_path)
    copied = migrate(tmp_path, legacy)
    assert len(copied) == 2
    assert (tmp_path / "config" / "user_configuration.yaml").read_text() == (
        "daemons: {old: {}}\n"
    )
    assert (tmp_path / "data" / "nameserver" / "ns_prod.sql").read_text() == "db"
    assert (legacy / "user_configuration.yaml").exists()  # originals untouched


def test_migration_never_overwrites(tmp_path):
    legacy = legacy_install(tmp_path)
    new_config = tmp_path / "config" / "user_configuration.yaml"
    new_config.parent.mkdir()
    new_config.write_text("daemons: {new: {}}\n")
    migrate(tmp_path, legacy)
    assert new_config.read_text() == "daemons: {new: {}}\n"


def test_migration_runs_once(tmp_path):
    legacy = legacy_install(tmp_path)
    migrate(tmp_path, legacy)
    (tmp_path / "config" / "user_configuration.yaml").unlink()  # `config reset`
    assert migrate(tmp_path, legacy) == []
    assert not (tmp_path / "config" / "user_configuration.yaml").exists()


def test_migration_without_legacy_install(tmp_path):
    assert migrate(tmp_path, tmp_path / "missing") == []
    assert not (tmp_path / "state").exists()  # no marker, nothing created


###############################################################################
# Importing pyrolab changes nothing global (#63) and creates nothing (#66)
###############################################################################


def test_import_has_no_side_effects(tmp_path):
    # Fresh interpreter, since this one has long since imported pyrolab.
    data_dir = tmp_path / "fresh-install"  # not the autouse fixture's dir
    code = textwrap.dedent(
        """
        import logging, sys, warnings
        filters = list(warnings.filters)
        import pyrolab, pyrolab.api, pyrolab.configure, pyrolab.manager
        import pyrolab.pyrolabd, pyrolab.server
        library_filters = list(warnings.filters)
        # The CLI is the `pyrolab` program rather than the library, and it
        # imports requests, whose urllib3 adds warning filters of its own.
        import pyrolab.cli

        problems = []
        if logging.getLogger().handlers:
            problems.append(f"root handlers: {logging.getLogger().handlers}")
        if sys.excepthook is not sys.__excepthook__:
            problems.append("sys.excepthook replaced")
        if library_filters != filters:
            problems.append("warning filters changed")
        handlers = logging.getLogger("pyrolab").handlers
        if [type(h).__name__ for h in handlers] != ["NullHandler"]:
            problems.append(f"pyrolab logger handlers: {handlers}")
        sys.exit("; ".join(problems) or 0)
        """
    )
    env = dict(os.environ, PYROLAB_DATA_DIR=str(data_dir))
    env.pop("PYROLAB_LOGFILE", None)
    result = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    # Regression: importing created the data and log directories, and a log
    # file for every process (#64, #66).
    assert not data_dir.exists()
