"""
ProcessManager and runner tests.

These exercise the manager's bookkeeping and the runners' setup logic
in-process. The only child process spawned is the ``multiprocessing.Manager``
server in ``test_shutdown_all_stops_the_real_manager_process``; nameserver and
daemon runners are never started.
"""

import multiprocessing
import queue
from datetime import datetime, timedelta

import pytest
from Pyro5.api import Proxy

from pyrolab.configure import DaemonConfiguration, ServiceConfiguration
from pyrolab.manager import (
    DaemonRunner,
    NameServerRunner,
    ProcessManager,
    running_time_human_readable,
)
from pyrolab.server import Lockable, LockableDaemon

###############################################################################
# running_time_human_readable
###############################################################################

START = datetime(2026, 1, 1, 12, 0, 0)


@pytest.mark.parametrize(
    "delta, expected",
    [
        (timedelta(seconds=0), "Up 0s"),
        (timedelta(seconds=45), "Up 45s"),
        # Regression: each of these was wrong (#77).
        (timedelta(seconds=60), "Up 1m 0s"),  # was "Up 60 seconds"
        (timedelta(days=1), "Up 1d 0h"),  # was "Up 1 days"
        (timedelta(days=6, hours=23, minutes=59), "Up 6d 23h"),  # was "Up 6 days"
        (timedelta(hours=1), "Up 1h 0m"),  # was "Up 60 minutes"
        (timedelta(minutes=2), "Up 2m 0s"),  # was "Up 1 minute"
        # Only the two most significant units are shown.
        (timedelta(hours=4, minutes=12, seconds=30), "Up 4h 12m"),
        (timedelta(days=400, hours=5), "Up 400d 5h"),
        # Sub-second precision is dropped, not rounded.
        (timedelta(seconds=59, milliseconds=999), "Up 59s"),
    ],
)
def test_running_time_human_readable(delta, expected):
    assert running_time_human_readable(START, START + delta) == expected


def test_running_time_defaults_to_now():
    assert running_time_human_readable(datetime.now()) == "Up 0s"


def test_running_time_clamps_negative_durations():
    # e.g. the system clock was set backwards after the process started
    assert running_time_human_readable(START, START - timedelta(hours=1)) == "Up 0s"


###############################################################################
# ProcessManager bookkeeping
###############################################################################


@pytest.fixture
def fresh_singleton(global_config):
    """Make ProcessManager.instance() build a new instance, then discard it."""
    ProcessManager._instance = None
    yield
    inst = ProcessManager._instance
    if inst is not None:
        inst.stop_checkup_timer()
    ProcessManager._instance = None


class FakeMultiprocessingManager:
    def __init__(self):
        self.shutdowns = 0

    def shutdown(self):
        self.shutdowns += 1


def test_instance_starts_checkup_timer_last(fresh_singleton, monkeypatch):
    # Regression: the timer was armed before .manager existed and before the
    # singleton was published (#75).
    monkeypatch.setattr(multiprocessing, "Manager", FakeMultiprocessingManager)
    seen = {}

    def record_state(self, duration=30.0):
        seen["has_manager"] = isinstance(
            getattr(self, "manager", None), FakeMultiprocessingManager
        )
        seen["published"] = ProcessManager._instance is self

    monkeypatch.setattr(ProcessManager, "start_checkup_timer", record_state)
    ProcessManager.instance()
    assert seen == {"has_manager": True, "published": True}


def test_shutdown_all_shuts_down_manager_once(fresh_singleton, monkeypatch):
    # Regression: the multiprocessing.Manager was never shut down (#75).
    monkeypatch.setattr(multiprocessing, "Manager", FakeMultiprocessingManager)
    pm = ProcessManager.instance()
    fake = pm.manager

    pm.shutdown_all()
    assert fake.shutdowns == 1
    assert ProcessManager._instance is None

    pm.shutdown_all()  # safe to call again
    assert fake.shutdowns == 1


def test_instance_after_shutdown_all_is_fresh(fresh_singleton, monkeypatch):
    monkeypatch.setattr(multiprocessing, "Manager", FakeMultiprocessingManager)
    first = ProcessManager.instance()
    first.shutdown_all()
    second = ProcessManager.instance()
    assert second is not first
    assert second.manager is not None


def test_shutdown_all_stops_the_real_manager_process(fresh_singleton):
    pm = ProcessManager.instance()
    server = pm.manager._process  # the Manager's server process
    assert server.is_alive()

    pm.shutdown_all()
    server.join(timeout=10)
    assert not server.is_alive()


def test_process_manager_cannot_be_constructed_directly():
    with pytest.raises(RuntimeError):
        ProcessManager()


def test_process_manager_has_no_shared_class_state():
    # Regression: class-level dicts shadowed the instance attributes (#74).
    assert "nameservers" not in vars(ProcessManager)
    assert "daemons" not in vars(ProcessManager)


###############################################################################
# Runners
###############################################################################


def test_nameserver_runner_requires_arguments():
    with pytest.raises(ValueError, match="name"):
        NameServerRunner(nsconfig=object(), msg_queue=object())
    with pytest.raises(ValueError, match="NameServerConfiguration"):
        NameServerRunner(name="ns", msg_queue=object())
    with pytest.raises(ValueError, match="queue"):
        NameServerRunner(name="ns", nsconfig=object())


@pytest.mark.parametrize("runner_cls", [NameServerRunner, DaemonRunner])
def test_runner_stops_on_none_sentinel(runner_cls):
    q = queue.Queue()
    if runner_cls is NameServerRunner:
        runner = NameServerRunner(name="ns", nsconfig=object(), msg_queue=q)
    else:
        runner = DaemonRunner(
            name="d",
            daemonconfig=None,
            serviceconfigs={},
            msg_queue=q,
            shared_uris={},
        )

    try:
        runner.process_message_queue()
        assert runner.stay_alive() is True

        q.put("ignored")
        runner.process_message_queue()
        assert runner.stay_alive() is True

        q.put(None)
        runner.process_message_queue()
        assert runner.stay_alive() is False
    finally:
        runner._timer.cancel()


def _daemon_runner(daemonconfig, serviceconfigs, shared_uris):
    return DaemonRunner(
        name="lab",
        daemonconfig=daemonconfig,
        serviceconfigs=serviceconfigs,
        msg_queue=queue.Queue(),
        shared_uris=shared_uris,
    )


def test_daemon_runner_setup_registers_services():
    serviceconfigs = {
        "sample.echo": ServiceConfiguration(
            module="pyrolab.drivers.sample", classname="SampleService"
        ),
        "sample.instrument": ServiceConfiguration(
            module="pyrolab.drivers.sample",
            classname="SampleAutoconnectInstrument",
            parameters={"address": "0.0.0.0", "port": 1234},
            instancemode="single",
        ),
    }
    shared_uris = {"stale": "should be cleared"}
    runner = _daemon_runner(
        DaemonConfiguration(host="localhost"), serviceconfigs, shared_uris
    )

    daemon, uris = runner.setup_daemon()
    try:
        assert set(uris) == {"sample.echo", "sample.instrument"}
        assert shared_uris == uris
        assert "lab" not in uris  # no nameservers, so no self-registration
    finally:
        daemon.close()


def test_daemon_runner_setup_self_registers_with_nameservers(serve):
    runner = _daemon_runner(
        DaemonConfiguration(
            host="localhost", classname="LockableDaemon", nameservers=["ns"]
        ),
        {
            "sample.instrument": ServiceConfiguration(
                module="pyrolab.drivers.sample",
                classname="SampleAutoconnectInstrument",
                parameters={"address": "0.0.0.0", "port": 1234},
                instancemode="single",
            )
        },
        {},
    )
    daemon, uris = runner.setup_daemon()
    assert isinstance(daemon, LockableDaemon)
    assert set(uris) == {"sample.instrument", "lab"}

    serve(daemon)
    with Proxy(uris["sample.instrument"]) as proxy:
        assert proxy.autoconnect() is True
        assert proxy.do_something() is True
    with Proxy(uris["lab"]) as proxy:
        assert proxy.ping() is True

    hosted = daemon.objectsById[uris["sample.instrument"].object]
    assert issubclass(hosted, Lockable)
