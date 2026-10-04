import os
import subprocess
import sys

import pytest
from Pyro5.errors import CommunicationError
from typer.testing import CliRunner

from pyrolab import __version__, cli
from pyrolab.configure import DaemonConfiguration, PyroLabConfiguration
from pyrolab.pyrolabd import InstanceInfo

runner = CliRunner()


class FakeDaemonProxy:
    """Stands in for the Pyro proxy to a running pyrolabd."""

    instances = []
    fail_bind = False
    # Return values for recorded calls, by method name (default True).
    returns = {}

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
            default = {"status": "running", "error": ""}
            return self.returns.get(
                name, default if name.startswith(("start_", "restart_")) else True
            )

        return record


@pytest.fixture
def running_daemon(data_dir, monkeypatch):
    """Pretend pyrolabd is up: write a lockfile and fake the proxy."""
    FakeDaemonProxy.instances = []
    FakeDaemonProxy.fail_bind = False
    FakeDaemonProxy.returns = {}
    monkeypatch.setattr(cli, "Proxy", FakeDaemonProxy)
    data_dir.LOCKFILE.write_text(
        InstanceInfo(pid=os.getpid(), uri="PYRO:pyrolabd@localhost:1").json()
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


@pytest.fixture
def dead_pid():
    """The PID of a process that has already exited."""
    proc = subprocess.run(
        [sys.executable, "-c", "import os; print(os.getpid())"],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(proc.stdout)


def test_stale_lockfile_means_not_running(data_dir, dead_pid):
    data_dir.LOCKFILE.write_text(
        InstanceInfo(pid=dead_pid, uri="PYRO:pyrolabd@localhost:1").json()
    )
    result = runner.invoke(cli.app, ["ps"])
    assert result.exit_code == 1
    assert "not running" in result.output


@pytest.mark.parametrize("contents", ["", "{", '{"pid": "x"}'])
def test_unreadable_lockfile_means_not_running(data_dir, contents):
    # Regression: a partially written lockfile raised a ValidationError (#56).
    data_dir.LOCKFILE.write_text(contents)
    result = runner.invoke(cli.app, ["ps"])
    assert result.exit_code == 1
    assert "not running" in result.output


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


@pytest.mark.parametrize(
    "kind, method, label",
    [
        ("nameserver", "stop_nameserver", "Nameserver"),
        ("daemon", "stop_daemon", "Daemon"),
    ],
)
def test_stop_something_not_running(running_daemon, kind, method, label):
    # Regression: an unknown name surfaced as a remote KeyError (#68).
    running_daemon.returns[method] = False
    result = runner.invoke(cli.app, ["stop", kind, "lockabl"])
    assert result.exit_code == 1
    assert f"{label} 'lockabl' is not running." in result.output


@pytest.mark.parametrize(
    "result, exit_code, message",
    [
        ({"status": "running", "error": ""}, 0, "Daemon 'd1' is running."),
        ({"status": "already running", "error": ""}, 0, "already running"),
        (
            {"status": "unknown", "error": ""},
            1,
            "There is no daemon named 'd1' in the configuration.",
        ),
        (
            {"status": "failed", "error": "OSError: port in use"},
            1,
            "Daemon 'd1' failed to start: OSError: port in use",
        ),
        ({"status": "timeout", "error": ""}, 1, "did not report ready in time"),
    ],
)
def test_start_reports_outcome(running_daemon, result, exit_code, message):
    # Regression: start always "succeeded", even if the process died at once
    # (#59).
    running_daemon.returns["start_daemon"] = result
    outcome = runner.invoke(cli.app, ["start", "daemon", "d1"])
    assert outcome.exit_code == exit_code
    assert message in outcome.output


@pytest.mark.parametrize("kind", ["nameserver", "daemon"])
def test_stop_requires_a_name(running_daemon, kind):
    # Regression: a missing name was passed through as None (#68).
    result = runner.invoke(cli.app, ["stop", kind])
    assert result.exit_code == 2  # usage error
    assert running_daemon.instances == []  # never reached the daemon


def test_reload(running_daemon, user_config):
    result = runner.invoke(cli.app, ["reload"])
    assert result.exit_code == 0, result.output
    assert "reloaded" in result.output
    assert running_daemon.instances[0].calls == [("reload",)]


def test_reload_failure_exits_nonzero(running_daemon, user_config):
    running_daemon.returns["reload"] = False
    result = runner.invoke(cli.app, ["reload"])
    assert result.exit_code == 1
    assert "reload failed" in result.output


def test_reload_without_user_config(running_daemon, data_dir):
    # Regression: the daemon crashed copying a missing file (#55).
    result = runner.invoke(cli.app, ["reload"])
    assert result.exit_code == 1
    assert "pyrolab config update" in result.output
    assert running_daemon.instances[0].calls == []


###############################################################################
# Update check
###############################################################################


def test_update_notice_goes_to_stderr(running_daemon, monkeypatch):
    monkeypatch.delenv("PYROLAB_NO_VERSION_CHECK")
    monkeypatch.setattr(cli.updates, "fetch_latest_version", lambda: "999.0.0")

    result = runner.invoke(cli.app, ["ps"])
    assert result.exit_code == 0, result.output
    assert "999.0.0" in result.stderr
    assert "999.0.0" not in result.stdout
    assert "FAKE PS OUTPUT" in result.stdout


def test_update_check_skipped_for_version_flag(data_dir, monkeypatch):
    monkeypatch.delenv("PYROLAB_NO_VERSION_CHECK")

    def fail():
        raise AssertionError("--version must not contact PyPI")

    monkeypatch.setattr(cli.updates, "fetch_latest_version", fail)
    result = runner.invoke(cli.app, ["--version"])
    assert result.exit_code == 0


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


def test_config_update_rejects_dangling_references(user_config, tmp_path):
    # Regression: a bad autolaunch entry was accepted, then killed the
    # background daemon at startup (#54).
    before = user_config.read_text()
    bad = tmp_path / "bad.yaml"
    bad.write_text("daemons:\n  d: {}\nautolaunch:\n  daemons: [d, typo]\n")

    result = runner.invoke(cli.app, ["config", "update", str(bad)])
    assert result.exit_code == 1
    assert "autolaunch refers to daemon 'typo', which is not defined" in result.output
    assert "not changed" in result.output
    assert user_config.read_text() == before


def test_config_update_missing_file(data_dir, tmp_path):
    result = runner.invoke(cli.app, ["config", "update", str(tmp_path / "x.yaml")])
    assert result.exit_code == 1
    assert "does not" in result.output


def test_info_with_invalid_config(data_dir):
    data_dir.RUNTIME_CONFIG.write_text("services:\n  s: {module: m, classname: C}\n")
    result = runner.invoke(cli.app, ["info"])
    assert result.exit_code == 1
    assert "daemon 'default' (the default), which is not defined" in result.output


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


@pytest.fixture
def config_with_spare_daemon(user_config):
    """The sample config plus a daemon that nothing refers to."""
    config = PyroLabConfiguration.from_file(user_config)
    config.daemons["spare"] = DaemonConfiguration()
    user_config.write_text(config.yaml())
    return user_config


@pytest.mark.parametrize(
    "kind, section, old",
    [
        ("nameserver", "nameservers", "persistent"),
        ("daemon", "daemons", "spare"),
        ("service", "services", "sample.echo"),
    ],
)
def test_rename(config_with_spare_daemon, kind, section, old):
    user_config = config_with_spare_daemon
    before = getattr(PyroLabConfiguration.from_file(user_config), section)[old]

    result = runner.invoke(cli.app, ["rename", kind, old, "renamed"])
    assert result.exit_code == 0, result.output

    entities = getattr(PyroLabConfiguration.from_file(user_config), section)
    assert old not in entities
    assert entities["renamed"] == before


@pytest.mark.parametrize(
    "kind, old, referrer",
    [
        ("nameserver", "local", "daemons.lockable"),
        ("daemon", "plain", "service 'sample.echo'"),
    ],
)
def test_rename_refuses_to_orphan_references(user_config, kind, old, referrer):
    # Renaming moves only the entry itself; with references left pointing at
    # the old name the config would be invalid, so nothing is written.
    before = user_config.read_text()
    result = runner.invoke(cli.app, ["rename", kind, old, "renamed"])
    assert result.exit_code == 1
    assert "still refer to it" in result.output
    assert f"'{old}'" in result.output
    assert user_config.read_text() == before


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
    def write_log(name, *lines):
        (data_dir.PYROLAB_LOGDIR / name).write_text("".join(f"{x}\n" for x in lines))

    write_log(
        "pyrolab_1.log",
        "[2026-01-01 10:00:00.000] INFO first",
        "[2026-01-01 10:00:02.000] ERROR third",
        "Traceback (most recent call last):",
        "  boom",
    )
    write_log(
        "pyrolab_2.log",
        "[2026-01-01 10:00:01.000] INFO second",
        "[2026-01-01 10:00:03.000] INFO fourth",
    )
    # Raw daemon output (tracebacks, no timestamps) is not merged.
    (data_dir.PYROLAB_LOGDIR / cli.DAEMON_OUTPUT_LOG).write_text(
        "Traceback (most recent call last):\nRuntimeError: boom\n"
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


###############################################################################
# pyrolab up
###############################################################################


class FakeDaemonProcess:
    """
    Stands in for the spawned pyrolabd. After ``ready_after`` polls it
    publishes a lockfile (or, if ``exit_code`` is set, exits instead).
    """

    def __init__(self, data_dir, ready_after=2, exit_code=None, error=None):
        self.data_dir = data_dir
        self.polls_left = ready_after
        self.exit_code = exit_code
        self.error = error
        self.returncode = None

    def poll(self):
        self.polls_left -= 1
        if self.polls_left > 0:
            return None
        if self.exit_code is None:
            self.data_dir.LOCKFILE.write_text(
                InstanceInfo(pid=os.getpid(), uri="PYRO:pyrolabd@localhost:1").json()
            )
            return None
        if self.error:
            self.data_dir.STARTUP_ERROR_FILE.write_text(self.error)
        self.returncode = self.exit_code
        return self.exit_code


@pytest.fixture
def spawn(data_dir, monkeypatch):
    """
    Replace process spawning; the daemon "responds" once its lockfile exists.
    Set ``spawn.process`` before invoking `up`; ``spawn.count`` records spawns.
    """

    class Spawn:
        process = FakeDaemonProcess(data_dir)
        count = 0

    def fake_spawn(port):
        Spawn.count += 1
        return Spawn.process

    monkeypatch.setattr(cli, "_spawn_daemon", fake_spawn)
    monkeypatch.setattr(cli, "_daemon_responds", lambda uri: data_dir.LOCKFILE.exists())
    monkeypatch.setattr(cli, "sleep", lambda seconds: None)
    return Spawn


def test_up_waits_until_daemon_responds(spawn):
    result = runner.invoke(cli.app, ["up"])
    assert result.exit_code == 0, result.output
    assert "PyroLab daemon is running." in result.output
    assert spawn.count == 1


def test_up_replaces_stale_lockfile(spawn, data_dir, dead_pid):
    data_dir.LOCKFILE.write_text(
        InstanceInfo(pid=dead_pid, uri="PYRO:pyrolabd@localhost:1").json()
    )
    result = runner.invoke(cli.app, ["up"])
    assert result.exit_code == 0, result.output
    assert spawn.count == 1


def test_up_when_already_running(spawn, data_dir):
    data_dir.LOCKFILE.write_text(
        InstanceInfo(pid=os.getpid(), uri="PYRO:pyrolabd@localhost:1").json()
    )
    result = runner.invoke(cli.app, ["up"])
    assert result.exit_code == 1
    assert "already running" in result.output
    assert spawn.count == 0


def test_up_when_running_but_not_responding(spawn, data_dir, monkeypatch):
    data_dir.LOCKFILE.write_text(
        InstanceInfo(pid=os.getpid(), uri="PYRO:pyrolabd@localhost:1").json()
    )
    monkeypatch.setattr(cli, "_daemon_responds", lambda uri: False)
    result = runner.invoke(cli.app, ["up"])
    assert result.exit_code == 1
    assert f"(pid {os.getpid()}) is running but not responding" in result.output
    assert spawn.count == 0  # never starts a second daemon
    assert data_dir.LOCKFILE.exists()


def test_up_reports_startup_error(spawn, data_dir):
    # Regression: `up` reported success while the daemon died at startup (#54).
    spawn.process = FakeDaemonProcess(
        data_dir, exit_code=1, error="invalid configuration in user.yaml"
    )
    result = runner.invoke(cli.app, ["up"])
    assert result.exit_code == 1
    assert "failed to start: invalid configuration in user.yaml" in result.output


def test_up_reports_unexplained_exit(spawn, data_dir):
    spawn.process = FakeDaemonProcess(data_dir, exit_code=3)
    result = runner.invoke(cli.app, ["up"])
    assert result.exit_code == 1
    assert "exited with code 3" in result.output


def test_up_ignores_previous_startup_error(spawn, data_dir):
    data_dir.STARTUP_ERROR_FILE.write_text("left over from last time")
    spawn.process = FakeDaemonProcess(data_dir, exit_code=3)
    result = runner.invoke(cli.app, ["up"])
    assert "left over" not in result.output


def test_up_times_out(spawn, data_dir):
    spawn.process = FakeDaemonProcess(data_dir, ready_after=10**9)
    result = runner.invoke(cli.app, ["up", "--timeout", "0"])
    assert result.exit_code == 1
    assert "did not respond within 0 seconds" in result.output


def test_spawned_daemon_output_goes_to_log_file(data_dir, monkeypatch):
    # Crashing child processes print tracebacks; they must not land in the
    # terminal that ran `pyrolab up`.
    seen = {}

    def fake_popen(args, **kwargs):
        seen["args"] = args
        seen.update(kwargs)
        return object()

    monkeypatch.setattr(cli.subprocess, "Popen", fake_popen)
    cli._spawn_daemon(port=None)
    assert seen["stdin"] is cli.subprocess.DEVNULL
    assert seen["stderr"] is cli.subprocess.STDOUT
    assert seen["stdout"].name == str(data_dir.PYROLAB_LOGDIR / cli.DAEMON_OUTPUT_LOG)
    assert seen["start_new_session"] is True
