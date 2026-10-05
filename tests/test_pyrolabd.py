import os
import threading

import pytest
from Pyro5.api import Proxy

from pyrolab import pyrolabd
from pyrolab.configure import PyroLabConfiguration
from pyrolab.pyrolabd import (
    InstanceInfo,
    PyroLabDaemon,
    read_lockfile,
    write_lockfile,
)


class FakeManager:
    """Stands in for ProcessManager; records calls instead of spawning."""

    def __init__(self):
        self.calls = []
        self.broken = set()  # names whose launch raises

    def launch_nameserver(self, name, wait=False):
        self.calls.append(("launch_nameserver", name) + (("wait",) if wait else ()))
        if name in self.broken:
            raise KeyError(name)
        return {"status": "running" if wait else "started", "error": ""}

    def launch_daemon(self, name, wait=False):
        self.calls.append(("launch_daemon", name) + (("wait",) if wait else ()))
        if name in self.broken:
            raise KeyError(name)
        return {"status": "running" if wait else "started", "error": ""}

    def shutdown_all(self):
        self.calls.append(("shutdown_all",))

    def shutdown_nameserver(self, name):
        self.calls.append(("shutdown_nameserver", name))
        return name != "not-running"

    def shutdown_daemon(self, name):
        self.calls.append(("shutdown_daemon", name))
        return name != "not-running"

    def reload(self):
        self.calls.append(("reload",))
        return True

    def get_nameserver_process_info(self, name):
        return {"created": "2026-01-01 00:00:00", "status": "Up 5 seconds", "uri": ""}

    def get_daemon_process_info(self, name):
        if name == "lockable":
            return {
                "created": "2026-01-01 00:00:00",
                "status": "Restarting in 12s (2/5)",
                "uri": "",
                "error": "RuntimeError: " + "x" * 100,
            }
        return {"created": "", "status": "Stopped", "uri": "", "error": ""}

    def get_service_process_info(self, name):
        return {"daemon": "", "uri": ""}


@pytest.fixture
def fake_manager(monkeypatch):
    fake = FakeManager()
    fake.instance_calls = 0

    def instance():
        fake.instance_calls += 1
        return fake

    monkeypatch.setattr(pyrolabd.ProcessManager, "instance", instance)
    return fake


@pytest.fixture
def pld(data_dir, global_config, fake_manager, sample_config_file):
    data_dir.USER_CONFIG_FILE.write_text(sample_config_file.read_text())
    return PyroLabDaemon()


def test_startup_writes_runtime_config(pld, data_dir):
    assert data_dir.RUNTIME_CONFIG.exists()
    assert PyroLabConfiguration.from_file(
        data_dir.RUNTIME_CONFIG
    ) == PyroLabConfiguration.from_file(data_dir.USER_CONFIG_FILE)


def test_startup_does_not_autolaunch(pld, fake_manager):
    # Autolaunch runs separately, in the background, once the daemon can
    # already answer requests.
    assert fake_manager.calls == []


def test_autolaunch_starts_nameservers_then_daemons(pld, fake_manager):
    pld.autolaunch()
    assert fake_manager.calls == [
        ("launch_nameserver", "local"),
        ("launch_daemon", "lockable"),
    ]


def test_autolaunch_continues_past_a_failing_entry(pld, fake_manager):
    # Regression: one failing entry stopped the rest, and killed the daemon
    # when it ran during startup (#54).
    fake_manager.broken = {"local"}
    pld.autolaunch()
    assert ("launch_daemon", "lockable") in fake_manager.calls


def test_invalid_user_config_fails_before_starting_anything(
    data_dir, global_config, fake_manager
):
    data_dir.USER_CONFIG_FILE.write_text("autolaunch:\n  daemons: [ghost]\n")
    with pytest.raises(ValueError, match="ghost"):
        PyroLabDaemon()
    assert fake_manager.instance_calls == 0  # process manager never started
    assert not data_dir.RUNTIME_CONFIG.exists()


def test_startup_without_user_config(data_dir, global_config, fake_manager):
    PyroLabDaemon()
    assert fake_manager.calls == []
    assert not data_dir.RUNTIME_CONFIG.exists()


def test_reload_picks_up_new_user_config(pld, data_dir, fake_manager):
    data_dir.USER_CONFIG_FILE.write_text(
        "daemons:\n  only-this-one:\n    host: localhost\n"
    )
    assert pld.reload() is True
    assert fake_manager.calls[-1] == ("reload",)
    assert set(pld.gconfig.get_config().daemons) == {"only-this-one"}
    assert "only-this-one" in data_dir.RUNTIME_CONFIG.read_text()


def test_reload_without_user_config(pld, data_dir, fake_manager):
    # Regression: raised FileNotFoundError inside the daemon (#55).
    before = data_dir.RUNTIME_CONFIG.read_text()
    data_dir.USER_CONFIG_FILE.unlink()  # as `pyrolab config reset` does

    assert pld.reload() is False
    assert ("reload",) not in fake_manager.calls  # nothing was restarted
    assert data_dir.RUNTIME_CONFIG.read_text() == before


@pytest.mark.parametrize("method", ["stop_nameserver", "stop_daemon"])
def test_stop_reports_whether_anything_was_running(pld, method):
    # The CLI relies on this to report an unknown name (#68).
    assert getattr(pld, method)("local") is True
    assert getattr(pld, method)("not-running") is False


def test_start_stop_restart_delegate_to_manager(pld, fake_manager):
    fake_manager.calls.clear()
    # Starting from the CLI waits until ready (#59); the result goes back.
    assert pld.start_daemon("plain") == {"status": "running", "error": ""}
    pld.stop_nameserver("local")
    assert pld.restart_daemon("plain")["status"] == "running"
    assert fake_manager.calls == [
        ("launch_daemon", "plain", "wait"),
        ("shutdown_nameserver", "local"),
        ("shutdown_daemon", "plain"),
        ("launch_daemon", "plain", "wait"),
    ]


def test_autolaunch_does_not_wait(pld, fake_manager):
    pld.autolaunch()
    assert all("wait" not in call for call in fake_manager.calls)


def test_ps_lists_every_configured_entity(pld):
    out = pld.ps()
    for header in ("NAMESERVER", "DAEMON", "SERVICE"):
        assert header in out
    for name in ("local", "persistent", "plain", "lockable"):
        assert name in out
    for name in ("sample.echo", "sample.instrument"):
        assert name in out
    assert "Up 5 seconds" in out
    assert "Stopped" in out


def test_ps_shows_last_error_truncated(pld):
    out = pld.ps()
    assert "LAST ERROR" in out
    assert "Restarting in 12s (2/5)" in out
    assert "RuntimeError: xxx" in out
    assert "x" * 100 not in out  # long errors are shortened


def test_ps_returns_plain_string(pld):
    # Exposed methods must return builtins so Pyro can serialize them.
    assert type(pld.ps()) is str


def test_instance_info_round_trip():
    ii = InstanceInfo(pid=1234, uri="PYRO:pyrolabd@localhost:5555")
    assert InstanceInfo.model_validate_json(ii.model_dump_json()) == ii


###############################################################################
# Lockfile
###############################################################################


def test_lockfile_round_trip(data_dir):
    info = InstanceInfo(pid=os.getpid(), uri="PYRO:pyrolabd@localhost:5555")
    write_lockfile(info)
    assert read_lockfile() == info
    # The temporary file was moved into place, not left behind.
    assert list(data_dir.root.glob("*.tmp")) == []


def test_write_lockfile_replaces_existing(data_dir):
    write_lockfile(InstanceInfo(pid=1, uri="PYRO:old@localhost:1"))
    write_lockfile(InstanceInfo(pid=2, uri="PYRO:new@localhost:2"))
    assert read_lockfile().uri == "PYRO:new@localhost:2"


@pytest.mark.parametrize("contents", [None, "", "{", '{"pid": 1}'])
def test_read_lockfile_missing_or_invalid(data_dir, contents):
    if contents is not None:
        data_dir.LOCKFILE.write_text(contents)
    assert read_lockfile() is None


###############################################################################
# main(): the background daemon process
###############################################################################


@pytest.fixture
def run_main(data_dir, global_config, fake_manager):
    """Run pyrolabd.main() in a thread; returns (thread, result dict)."""
    started = []

    def start():
        result = {}
        thread = threading.Thread(
            target=lambda: result.update(code=pyrolabd.main(port=0)), daemon=True
        )
        thread.start()
        started.append(thread)
        return thread, result

    yield start
    for thread in started:
        thread.join(timeout=10)


def test_main_publishes_lockfile_then_autolaunches_and_shuts_down(
    run_main, data_dir, fake_manager, sample_config_file, wait_for
):
    data_dir.USER_CONFIG_FILE.write_text(sample_config_file.read_text())
    thread, result = run_main()

    info = wait_for(read_lockfile)
    assert info is not None and info.pid == os.getpid()
    assert wait_for(lambda: ("launch_daemon", "lockable") in fake_manager.calls)

    with Proxy(info.uri) as proxy:
        assert "at" in proxy.whoami()
        proxy.shutdown()

    thread.join(timeout=10)
    assert result["code"] == 0
    assert ("shutdown_all",) in fake_manager.calls
    assert not data_dir.LOCKFILE.exists()
    assert not data_dir.RUNTIME_CONFIG.exists()


def test_main_reports_invalid_config(run_main, data_dir, fake_manager):
    data_dir.USER_CONFIG_FILE.write_text("autolaunch:\n  nameservers: [ghost]\n")
    thread, result = run_main()
    thread.join(timeout=10)

    assert result["code"] == 1
    message = data_dir.STARTUP_ERROR_FILE.read_text()
    assert "invalid configuration" in message
    assert "autolaunch refers to nameserver 'ghost'" in message
    assert not data_dir.LOCKFILE.exists()
    assert fake_manager.instance_calls == 0


def test_main_refuses_to_start_twice(run_main, data_dir):
    other = InstanceInfo(pid=os.getpid(), uri="PYRO:pyrolabd@localhost:1")
    write_lockfile(other)
    thread, result = run_main()
    thread.join(timeout=10)

    assert result["code"] == 1
    assert "already running" in data_dir.STARTUP_ERROR_FILE.read_text()
    assert read_lockfile() == other  # the running daemon's lockfile is untouched


###############################################################################
# The daemon owns the log (#25, #64)
###############################################################################


def test_main_writes_the_log_and_cleans_up(
    run_main, data_dir, sample_config_file, wait_for
):
    import logging

    from pyrolab import logs

    handlers_before = list(logging.getLogger().handlers)
    data_dir.USER_CONFIG_FILE.write_text(sample_config_file.read_text())
    thread, result = run_main()
    info = wait_for(read_lockfile)
    with Proxy(info.uri) as proxy:
        proxy.shutdown()
    thread.join(timeout=10)

    entries, skipped = logs.read_entries(logs.log_files(data_dir.PYROLAB_LOGFILE))
    assert skipped == 0
    assert entries[0]["event"] == logs.DAEMON_START_EVENT
    assert any("listening at" in e["message"] for e in entries)
    assert logging.getLogger().handlers == handlers_before  # handler removed


def test_refused_daemon_does_not_touch_the_log(run_main, data_dir):
    write_lockfile(InstanceInfo(pid=os.getpid(), uri="PYRO:pyrolabd@localhost:1"))
    thread, result = run_main()
    thread.join(timeout=10)
    assert result["code"] == 1
    assert not data_dir.PYROLAB_LOGFILE.exists()  # never a second writer


def test_main_copies_legacy_files(run_main, data_dir, wait_for):
    legacy = data_dir.LEGACY_DATA_DIR
    legacy.mkdir()
    (legacy / "user_configuration.yaml").write_text("daemons: {old: {}}\n")
    thread, result = run_main()
    info = wait_for(read_lockfile)
    with Proxy(info.uri) as proxy:
        proxy.shutdown()
    thread.join(timeout=10)
    assert data_dir.USER_CONFIG_FILE.read_text() == "daemons: {old: {}}\n"
