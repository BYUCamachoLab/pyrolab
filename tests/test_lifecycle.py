"""
ProcessManager lifecycle: launching, stopping, crash recovery, and status.

Runners are replaced with FakeProcess, which behaves like a real runner (it
exits on the stop message unless told to hang) without spawning anything, and
the manager's clock is a FakeClock, so the restart backoff can be tested
without waiting minutes.
"""

import queue
import time

import pytest

from pyrolab import manager as mgr
from pyrolab.manager import ProcessManager


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class FakeProcess:
    """
    Stands in for a NameServerRunner/DaemonRunner.

    ``hang`` makes it ignore: "stop" (the stop message; dies on terminate),
    "terminate" (dies only on kill), or "kill" (can't be killed). ``ready``
    controls whether it reports ready on start; ``fail`` makes it die on
    start with that error.
    """

    def __init__(self, msg_queue, shared_state, hang=None, ready=True, fail=None):
        self.msg_queue = msg_queue
        self.state = shared_state
        self.hang = hang
        self.ready = ready
        self.fail = fail
        self.alive = False
        self.exitcode = None
        self.calls = []

    def _die(self, code):
        self.alive = False
        self.exitcode = code

    def start(self):
        self.calls.append("start")
        self.alive = True
        if self.fail:
            self.state["error"] = self.fail
            self._die(1)
        elif self.ready:
            self.state["ready"] = True

    def is_alive(self):
        if self.alive and self.hang is None:
            try:
                if self.msg_queue.get_nowait() is None:
                    self._die(0)
            except queue.Empty:
                pass
        return self.alive

    def join(self, timeout=None):
        self.calls.append("join")
        if self.is_alive() and timeout:
            time.sleep(timeout)  # like a real join on a process that won't exit

    def terminate(self):
        self.calls.append("terminate")
        if self.hang in (None, "stop"):
            self._die(-15)

    def kill(self):
        self.calls.append("kill")
        if self.hang != "kill":
            self._die(-9)

    def crash(self, code=1, error=None):
        if error:
            self.state["error"] = error
        self._die(code)


@pytest.fixture(autouse=True)
def short_grace(monkeypatch):
    monkeypatch.setattr(mgr, "STOP_GRACE", 0.2)
    monkeypatch.setattr(mgr, "TERMINATE_GRACE", 0.05)


@pytest.fixture
def removed(monkeypatch):
    """Records remove_registrations calls instead of contacting nameservers."""
    calls = []
    monkeypatch.setattr(
        mgr, "remove_registrations", lambda nameservers, names: calls.append(names)
    )
    return calls


@pytest.fixture
def pm(global_config, sample_config_file, removed):
    """
    A ProcessManager over the sample config whose runners are FakeProcesses.
    Set ``pm.behavior[name]`` to FakeProcess keyword arguments before
    launching; ``pm.spawned[name]`` lists every process started for a name.
    """
    global_config.load_config(sample_config_file)
    pm = ProcessManager.__new__(ProcessManager)
    pm.nameservers = {}
    pm.daemons = {}
    pm.GLOBAL_CONFIG = global_config
    pm.clock = FakeClock()
    pm._clock = pm.clock
    pm._shared_dict = dict
    pm._message_queue = queue.Queue
    pm.start_checkup_timer = lambda *args, **kwargs: None
    pm.stop_checkup_timer = lambda: None
    pm.behavior = {}
    pm.spawned = {}

    def create_runner(kind, name, msg_queue, shared_state, uris):
        process = FakeProcess(msg_queue, shared_state, **pm.behavior.get(name, {}))
        process.name = name
        if kind == mgr.DAEMON:
            process.daemonconfig = global_config.get_daemon_config(name)
            process.serviceconfigs = global_config.get_service_configs_for_daemon(name)
        else:
            process.nsconfig = global_config.get_nameserver_config(name)
        pm.spawned.setdefault(name, []).append(process)
        return process

    pm._create_runner = create_runner
    return pm


def current(pm, name):
    return pm.spawned[name][-1]


###############################################################################
# Launching (#59)
###############################################################################


def test_launch_and_wait_until_ready(pm):
    assert pm.launch_daemon("plain", wait=True) == {"status": "running", "error": ""}
    assert pm.get_daemon_process_info("plain")["status"] == "Up 0s"


def test_launch_without_waiting(pm):
    assert pm.launch_daemon("plain")["status"] == "started"


def test_launch_reports_startup_failure(pm):
    pm.behavior["plain"] = {"fail": "ModuleNotFoundError: No module named 'x'"}
    assert pm.launch_daemon("plain", wait=True) == {
        "status": "failed",
        "error": "ModuleNotFoundError: No module named 'x'",
    }


def test_launch_reports_exit_code_without_error(pm):
    pm.behavior["plain"] = {"ready": False}
    pm.launch_daemon("plain")
    current(pm, "plain").crash(code=3)
    result = pm._await_ready(pm.daemons["plain"], timeout=1)
    assert result == {"status": "failed", "error": "exited with code 3"}


def test_launch_times_out(pm):
    pm.behavior["plain"] = {"ready": False}
    result = pm.launch_daemon("plain", wait=True, timeout=0.05)
    assert result["status"] == "timeout"
    assert pm.get_daemon_process_info("plain")["status"] == "Starting"


def test_launch_unknown_name(pm):
    assert pm.launch_daemon("nope", wait=True)["status"] == "unknown"
    assert pm.spawned == {}


def test_launch_when_already_running_does_not_spawn_twice(pm):
    # Previously a second launch silently orphaned the first process.
    pm.launch_daemon("plain", wait=True)
    assert pm.launch_daemon("plain", wait=True)["status"] == "already running"
    assert len(pm.spawned["plain"]) == 1


def test_launch_spawn_error_is_reported(pm, monkeypatch):
    def broken(*args):
        raise OSError("too many open files")

    pm._create_runner = broken
    result = pm.launch_daemon("plain", wait=True)
    assert result == {"status": "failed", "error": "OSError: too many open files"}
    assert "plain" not in pm.daemons


###############################################################################
# Stopping (#50, #68)
###############################################################################


def test_stop_unknown(pm):
    assert pm.shutdown_daemon("nope") is False


def test_stop_clean_exit(pm):
    pm.launch_daemon("plain", wait=True)
    assert pm.shutdown_daemon("plain") is True
    assert "plain" not in pm.daemons
    assert "terminate" not in current(pm, "plain").calls


@pytest.mark.parametrize(
    "hang, escalation",
    [("stop", ["terminate"]), ("terminate", ["terminate", "kill"])],
)
def test_stop_escalates_until_dead(pm, removed, hang, escalation):
    # Regression: shutdown assumed success after a fixed sleep, forgetting a
    # process that was still running (#50).
    pm.behavior["plain"] = {"hang": hang}
    pm.launch_daemon("plain", wait=True)

    assert pm.shutdown_daemon("plain") is True
    calls = current(pm, "plain").calls
    assert [c for c in calls if c in ("terminate", "kill")] == escalation
    assert "plain" not in pm.daemons
    # It couldn't deregister itself, so the manager did it.
    assert removed == [{"local": ["sample.echo"]}]


def test_stop_unkillable_process_is_reported_and_kept(pm):
    pm.behavior["plain"] = {"hang": "kill"}
    pm.launch_daemon("plain", wait=True)
    assert pm.shutdown_daemon("plain") is False
    assert "plain" in pm.daemons  # not forgotten while still running


def test_clean_stop_does_not_touch_registrations(pm, removed):
    pm.launch_daemon("plain", wait=True)
    pm.shutdown_daemon("plain")
    assert removed == []  # the runner deregisters itself


def test_stopping_several_waits_for_them_together(pm):
    pm.behavior["plain"] = {"hang": "stop"}
    pm.behavior["lockable"] = {"hang": "stop"}
    pm.launch_daemon("plain", wait=True)
    pm.launch_daemon("lockable", wait=True)

    began = time.monotonic()
    results = pm._stop_many([(mgr.DAEMON, "plain"), (mgr.DAEMON, "lockable")])
    elapsed = time.monotonic() - began

    assert all(results.values())
    # One shared grace period (0.2s), not one each (0.4s).
    assert elapsed < 0.35


def test_stop_crashed_process(pm):
    pm.launch_daemon("plain", wait=True)
    current(pm, "plain").crash()
    pm.checkup(continuous=False)  # now waiting to restart
    assert pm.shutdown_daemon("plain") is True
    assert "plain" not in pm.daemons
    pm.clock.advance(3600)
    pm.checkup(continuous=False)
    assert len(pm.spawned["plain"]) == 1  # and it stays stopped


###############################################################################
# Crash recovery (#51)
###############################################################################


def test_crash_schedules_restart_with_backoff(pm):
    pm.launch_daemon("plain", wait=True)
    current(pm, "plain").crash(error="RuntimeError: device unplugged")

    pm.checkup(continuous=False)
    info = pm.get_daemon_process_info("plain")
    assert info["status"] == "Restarting in 5s (1/5)"
    assert info["error"] == "RuntimeError: device unplugged"

    pm.clock.advance(4)
    pm.checkup(continuous=False)
    assert len(pm.spawned["plain"]) == 1  # not yet

    pm.clock.advance(1)
    pm.checkup(continuous=False)
    assert len(pm.spawned["plain"]) == 2
    assert pm.get_daemon_process_info("plain")["status"] == "Up 0s"


def test_crash_without_error_reports_exit_code(pm):
    pm.launch_daemon("plain", wait=True)
    current(pm, "plain").crash(code=-11)
    pm.checkup(continuous=False)
    assert pm.get_daemon_process_info("plain")["error"] == "exited with code -11"


def test_backoff_then_give_up_after_five_crashes(pm, removed):
    pm.launch_daemon("plain", wait=True)
    delays = []
    for _ in range(5):
        current(pm, "plain").crash(error="RuntimeError: boom")
        pm.checkup(continuous=False)
        group = pm.daemons["plain"]
        if group.status == mgr.RESTARTING:
            delays.append(group.retry_at - pm.clock())
            pm.clock.advance(delays[-1])
            pm.checkup(continuous=False)

    assert delays == [5, 15, 60, 300]
    info = pm.get_daemon_process_info("plain")
    assert info["status"] == "Failed (5 crashes)"
    assert info["error"] == "RuntimeError: boom"
    # Registrations pointing at the dead daemon are cleaned up.
    assert removed == [{"local": ["sample.echo"]}]

    pm.clock.advance(86400)
    pm.checkup(continuous=False)
    assert len(pm.spawned["plain"]) == 5  # no more restarts


def test_stable_uptime_resets_failure_count(pm):
    pm.launch_daemon("plain", wait=True)
    for _ in range(3):
        current(pm, "plain").crash()
        pm.checkup(continuous=False)
        pm.clock.advance(pm.daemons["plain"].retry_at - pm.clock())
        pm.checkup(continuous=False)
    assert pm.daemons["plain"].failures == 3

    pm.clock.advance(mgr.STABLE_UPTIME)  # healthy for ten minutes
    current(pm, "plain").crash()
    pm.checkup(continuous=False)
    assert pm.daemons["plain"].failures == 1
    assert pm.get_daemon_process_info("plain")["status"].startswith("Restarting in 5s")


def test_manual_start_revives_failed_entity(pm):
    pm.launch_daemon("plain", wait=True)
    pm.daemons["plain"].failures = mgr.MAX_CONSECUTIVE_FAILURES - 1
    current(pm, "plain").crash()
    pm.checkup(continuous=False)
    assert pm.daemons["plain"].status == mgr.FAILED

    assert pm.launch_daemon("plain", wait=True)["status"] == "running"
    assert pm.daemons["plain"].failures == 0
    assert pm.get_daemon_process_info("plain")["error"] == ""


def test_restart_that_cannot_spawn_counts_as_a_crash(pm):
    pm.launch_daemon("plain", wait=True)
    current(pm, "plain").crash()
    pm.checkup(continuous=False)

    def broken(*args):
        raise OSError("no more processes")

    pm._create_runner = broken
    pm.clock.advance(5)
    pm.checkup(continuous=False)
    group = pm.daemons["plain"]
    assert group.failures == 2
    assert group.last_error == "OSError: no more processes"


###############################################################################
# Reload (#59)
###############################################################################


def test_reload_restarts_and_reports_success(pm):
    pm.launch_nameserver("local", wait=True)
    pm.launch_daemon("plain", wait=True)
    assert pm.reload() is True
    assert len(pm.spawned["local"]) == 2
    assert len(pm.spawned["plain"]) == 2


def test_reload_reports_failure(pm):
    pm.launch_daemon("plain", wait=True)
    pm.behavior["plain"] = {"fail": "ValueError: bad parameter"}
    assert pm.reload() is False


def test_reload_drops_entities_removed_from_config(pm):
    pm.launch_daemon("plain", wait=True)
    del pm.GLOBAL_CONFIG.config.daemons["plain"]
    assert pm.reload() is True
    assert "plain" not in pm.daemons


def test_reload_revives_failed_entity(pm):
    pm.launch_daemon("plain", wait=True)
    pm.daemons["plain"].failures = mgr.MAX_CONSECUTIVE_FAILURES - 1
    current(pm, "plain").crash()
    pm.checkup(continuous=False)
    assert pm.reload() is True
    assert pm.daemons["plain"].status == mgr.RUNNING


###############################################################################
# Status reporting
###############################################################################


def test_info_when_not_running(pm):
    assert pm.get_nameserver_process_info("local") == {
        "created": "",
        "status": "Stopped",
        "error": "",
        "uri": "",
    }


def test_nameserver_info(pm):
    pm.launch_nameserver("local", wait=True)
    info = pm.get_nameserver_process_info("local")
    assert info["status"] == "Up 0s"
    assert info["uri"] == "localhost:9090"


def test_info_for_process_that_just_died(pm):
    pm.launch_nameserver("local", wait=True)
    current(pm, "local").crash(error="OSError: address in use")
    info = pm.get_nameserver_process_info("local")
    assert info["status"] == "Died"
    assert info["error"] == "OSError: address in use"  # before checkup runs


def test_daemon_uri(pm):
    pm.launch_daemon("lockable", wait=True)
    assert pm.get_daemon_process_info("lockable")["uri"] == ""
    pm.daemons["lockable"].shared_uris["lockable"] = "PYRO:d@localhost:1"
    assert pm.get_daemon_process_info("lockable")["uri"] == "PYRO:d@localhost:1"


def test_service_info_before_uri_is_published(pm):
    # Regression: raised KeyError while the daemon was still starting (#46).
    pm.launch_daemon("plain", wait=True)
    assert pm.get_service_process_info("sample.echo") == {"daemon": "plain", "uri": ""}
    pm.daemons["plain"].shared_uris["sample.echo"] = "PYRO:svc@localhost:1"
    assert pm.get_service_process_info("sample.echo")["uri"] == "PYRO:svc@localhost:1"


def test_service_info_for_unknown_service(pm):
    assert pm.get_service_process_info("svc") == {"daemon": "", "uri": ""}
