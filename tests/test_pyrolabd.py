import pytest

from pyrolab import pyrolabd
from pyrolab.configure import PyroLabConfiguration
from pyrolab.pyrolabd import InstanceInfo, PyroLabDaemon


class FakeManager:
    """Stands in for ProcessManager; records calls instead of spawning."""

    def __init__(self):
        self.calls = []

    def launch_nameserver(self, name):
        self.calls.append(("launch_nameserver", name))

    def launch_daemon(self, name):
        self.calls.append(("launch_daemon", name))

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
        return {"created": "", "status": "Stopped", "uri": ""}

    def get_service_process_info(self, name):
        return {"daemon": "", "uri": ""}


@pytest.fixture
def fake_manager(monkeypatch):
    fake = FakeManager()
    monkeypatch.setattr(pyrolabd.ProcessManager, "instance", lambda: fake)
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


def test_startup_autolaunches_nameservers_then_daemons(pld, fake_manager):
    assert fake_manager.calls == [
        ("launch_nameserver", "local"),
        ("launch_daemon", "lockable"),
    ]


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
    pld.start_daemon("plain")
    pld.stop_nameserver("local")
    pld.restart_daemon("plain")
    assert fake_manager.calls == [
        ("launch_daemon", "plain"),
        ("shutdown_nameserver", "local"),
        ("shutdown_daemon", "plain"),
        ("launch_daemon", "plain"),
    ]


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


def test_ps_returns_plain_string(pld):
    # Exposed methods must return builtins so Pyro can serialize them.
    assert type(pld.ps()) is str


def test_instance_info_round_trip():
    ii = InstanceInfo(pid=1234, uri="PYRO:pyrolabd@localhost:5555")
    assert InstanceInfo.parse_raw(ii.json()) == ii
