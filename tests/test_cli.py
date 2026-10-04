import os

import pytest
from Pyro5.errors import CommunicationError
from typer.testing import CliRunner

from pyrolab import __version__, cli
from pyrolab.configure import PyroLabConfiguration
from pyrolab.pyrolabd import InstanceInfo

runner = CliRunner()


class FakeDaemonProxy:
    """Stands in for the Pyro proxy to a running pyrolabd."""

    instances = []
    fail_bind = False

    def __init__(self, uri):
        self.uri = uri
        self.calls = []
        FakeDaemonProxy.instances.append(self)

    def _pyroBind(self):
        if self.fail_bind:
            raise CommunicationError("connection refused")

    def ps(self):
        return "FAKE PS OUTPUT"

    def __getattr__(self, name):
        def record(*args):
            self.calls.append((name, *args))

        return record


@pytest.fixture
def running_daemon(data_dir, monkeypatch):
    """Pretend pyrolabd is up: write a lockfile and fake the proxy."""
    FakeDaemonProxy.instances = []
    FakeDaemonProxy.fail_bind = False
    monkeypatch.setattr(cli, "Proxy", FakeDaemonProxy)
    data_dir.LOCKFILE.write_text(
        InstanceInfo(pid=1, uri="PYRO:pyrolabd@localhost:1").json()
    )
    return FakeDaemonProxy


@pytest.fixture
def user_config(data_dir, sample_config_file):
    data_dir.USER_CONFIG_FILE.write_text(sample_config_file.read_text())
    return data_dir.USER_CONFIG_FILE


def test_version():
    result = runner.invoke(cli.app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"PyroLab {__version__}"


###############################################################################
# Talking to the background daemon
###############################################################################


def test_command_without_daemon_aborts(data_dir):
    result = runner.invoke(cli.app, ["ps"])
    assert result.exit_code == 1
    assert "not running" in result.output


def test_get_daemon_without_abort_returns_none(data_dir):
    assert cli.get_daemon(abort=False) is None


def test_get_daemon_unreachable(running_daemon):
    running_daemon.fail_bind = True
    with pytest.raises(ConnectionRefusedError):
        cli.get_daemon()


def test_ps(running_daemon):
    result = runner.invoke(cli.app, ["ps"])
    assert result.exit_code == 0
    assert "FAKE PS OUTPUT" in result.output
    assert running_daemon.instances[0].uri == "PYRO:pyrolabd@localhost:1"


@pytest.mark.parametrize(
    "args, call",
    [
        (["start", "nameserver", "ns1"], ("start_nameserver", "ns1")),
        (["start", "daemon", "d1"], ("start_daemon", "d1")),
        (["stop", "nameserver", "ns1"], ("stop_nameserver", "ns1")),
        (["stop", "daemon", "d1"], ("stop_daemon", "d1")),
    ],
)
def test_start_stop_commands(running_daemon, args, call):
    result = runner.invoke(cli.app, args)
    assert result.exit_code == 0, result.output
    assert running_daemon.instances[0].calls == [call]


def test_reload_message_when_user_config_is_newer(running_daemon, data_dir):
    data_dir.RUNTIME_CONFIG.write_text("")
    data_dir.USER_CONFIG_FILE.write_text("")
    os.utime(data_dir.RUNTIME_CONFIG, (1_000_000, 1_000_000))
    os.utime(data_dir.USER_CONFIG_FILE, (2_000_000, 2_000_000))

    result = runner.invoke(cli.app, ["ps"])
    assert "pyrolab reload" in result.output


def test_no_reload_message_when_runtime_config_is_current(running_daemon, data_dir):
    data_dir.USER_CONFIG_FILE.write_text("")
    data_dir.RUNTIME_CONFIG.write_text("")
    os.utime(data_dir.USER_CONFIG_FILE, (1_000_000, 1_000_000))
    os.utime(data_dir.RUNTIME_CONFIG, (2_000_000, 2_000_000))

    result = runner.invoke(cli.app, ["ps"])
    assert "pyrolab reload" not in result.output


def test_commands_work_after_config_reset(running_daemon, data_dir):
    # Regression: get_daemon stat'ed a missing USER_CONFIG_FILE (#70).
    data_dir.RUNTIME_CONFIG.write_text("")
    assert not data_dir.USER_CONFIG_FILE.exists()

    result = runner.invoke(cli.app, ["ps"])
    assert result.exit_code == 0, result.output


###############################################################################
# pyrolab config
###############################################################################


def test_config_update(data_dir, sample_config_file):
    result = runner.invoke(cli.app, ["config", "update", str(sample_config_file)])
    assert result.exit_code == 0, result.output
    assert PyroLabConfiguration.from_file(
        data_dir.USER_CONFIG_FILE
    ) == PyroLabConfiguration.from_file(sample_config_file)


def test_config_reset_confirmed(user_config):
    result = runner.invoke(cli.app, ["config", "reset"], input="y\n")
    assert result.exit_code == 0
    assert not user_config.exists()


def test_config_reset_declined(user_config):
    result = runner.invoke(cli.app, ["config", "reset"], input="n\n")
    assert result.exit_code == 0
    assert "No changes made" in result.output
    assert user_config.exists()


def test_config_export(user_config, tmp_path):
    out = tmp_path / "exported.yaml"
    result = runner.invoke(cli.app, ["config", "export", str(out)])
    assert result.exit_code == 0
    assert out.read_text() == user_config.read_text()


def test_config_export_without_config(data_dir, tmp_path):
    result = runner.invoke(cli.app, ["config", "export", str(tmp_path / "x.yaml")])
    assert result.exit_code == 1
    assert "No configuration file found" in result.output


###############################################################################
# pyrolab info
###############################################################################


def test_info_without_config(data_dir):
    result = runner.invoke(cli.app, ["info"])
    assert "No configuration installed" in result.output


def test_info_shows_user_config(user_config):
    result = runner.invoke(cli.app, ["info"])
    assert result.exit_code == 0, result.output
    for text in ("Nameservers", "Daemons", "Services", "persistent", "sample.echo"):
        assert text in result.output


def test_info_prefers_runtime_config(user_config, data_dir):
    data_dir.RUNTIME_CONFIG.write_text(
        "daemons:\n  running-daemon:\n    host: localhost\n"
    )
    result = runner.invoke(cli.app, ["info"])
    assert "running-daemon" in result.output
    assert "sample.echo" not in result.output


###############################################################################
# pyrolab rename
###############################################################################


@pytest.mark.parametrize(
    "kind, section, old",
    [
        ("nameserver", "nameservers", "local"),
        ("daemon", "daemons", "plain"),
        ("service", "services", "sample.echo"),
    ],
)
def test_rename(user_config, kind, section, old):
    before = getattr(PyroLabConfiguration.from_file(user_config), section)[old]

    result = runner.invoke(cli.app, ["rename", kind, old, "renamed"])
    assert result.exit_code == 0, result.output

    entities = getattr(PyroLabConfiguration.from_file(user_config), section)
    assert old not in entities
    assert entities["renamed"] == before


def test_rename_unknown_nameserver(user_config):
    before = user_config.read_text()
    result = runner.invoke(cli.app, ["rename", "nameserver", "nope", "new"])
    assert "Nameserver not found" in result.output
    assert user_config.read_text() == before


def test_rename_without_config(data_dir):
    result = runner.invoke(cli.app, ["rename", "daemon", "a", "b"])
    assert "No user configuration file found" in result.output


###############################################################################
# pyrolab logs
###############################################################################


def test_logs_export_merges_and_sorts(data_dir, tmp_path):
    (data_dir.PYROLAB_LOGDIR / "pyrolab_1.log").write_text(
        "[2026-01-01 10:00:00.000] INFO first\n"
        "[2026-01-01 10:00:02.000] ERROR third\n"
        "Traceback (most recent call last):\n"
        "  boom\n"
    )
    (data_dir.PYROLAB_LOGDIR / "pyrolab_2.log").write_text(
        "[2026-01-01 10:00:01.000] INFO second\n[2026-01-01 10:00:03.000] INFO fourth\n"
    )
    out = tmp_path / "merged.log"

    result = runner.invoke(cli.app, ["logs", "export", str(out)])
    assert result.exit_code == 0, result.output
    assert out.read_text().splitlines() == [
        "[2026-01-01 10:00:00.000] INFO first",
        "[2026-01-01 10:00:01.000] INFO second",
        "[2026-01-01 10:00:02.000] ERROR third",
        "Traceback (most recent call last):",
        "  boom",
        "[2026-01-01 10:00:03.000] INFO fourth",
    ]


def test_logs_clean(data_dir):
    for i in range(3):
        (data_dir.PYROLAB_LOGDIR / f"pyrolab_{i}.log").write_text("x\n")
    result = runner.invoke(cli.app, ["logs", "clean"])
    assert result.exit_code == 0
    assert list(data_dir.PYROLAB_LOGDIR.iterdir()) == []
