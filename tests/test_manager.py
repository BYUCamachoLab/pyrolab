"""
ProcessManager and runner tests.

These exercise the manager's bookkeeping and the runners' setup logic
in-process. Nothing here spawns a child process.
"""

import queue
from datetime import datetime, timedelta
from types import SimpleNamespace

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
        (timedelta(seconds=0), "Up 0 seconds"),
        (timedelta(seconds=45), "Up 45 seconds"),
        (timedelta(seconds=90), "Up 1 minute"),
        (timedelta(minutes=5, seconds=10), "Up 5 minutes"),
        (timedelta(hours=3, minutes=20), "Up 3 hours"),
        (timedelta(days=4, hours=2), "Up 4 days"),
    ],
)
def test_running_time_human_readable(delta, expected):
    assert running_time_human_readable(START, START + delta) == expected


def test_running_time_defaults_to_now():
    assert running_time_human_readable(datetime.now()) == "Up 0 seconds"


###############################################################################
# ProcessManager bookkeeping
###############################################################################


@pytest.fixture
def manager():
    """
    A ProcessManager built without ``instance()``, which would start a
    checkup timer and a ``multiprocessing.Manager`` server process.
    """
    pm = ProcessManager.__new__(ProcessManager)
    pm.nameservers = {}
    pm.daemons = {}
    return pm


def fake_process(alive=True, **attrs):
    return SimpleNamespace(is_alive=lambda: alive, **attrs)


def test_process_manager_cannot_be_constructed_directly():
    with pytest.raises(RuntimeError):
        ProcessManager()


def test_process_manager_has_no_shared_class_state():
    # Regression: class-level dicts shadowed the instance attributes (#74).
    assert "nameservers" not in vars(ProcessManager)
    assert "daemons" not in vars(ProcessManager)


def test_nameserver_info_when_not_running(manager):
    assert manager.get_nameserver_process_info("ns") == {
        "created": "",
        "status": "Stopped",
        "uri": "",
    }


def test_nameserver_info_when_running(manager):
    nsconfig = SimpleNamespace(host="localhost", ns_port=9090)
    manager.nameservers["ns"] = SimpleNamespace(
        process=fake_process(nsconfig=nsconfig), created=START
    )
    info = manager.get_nameserver_process_info("ns")
    assert info["created"] == "2026-01-01 12:00:00"
    assert info["status"].startswith("Up ")
    assert info["uri"] == "localhost:9090"


def test_nameserver_info_when_dead(manager):
    nsconfig = SimpleNamespace(host="localhost", ns_port=9090)
    manager.nameservers["ns"] = SimpleNamespace(
        process=fake_process(alive=False, nsconfig=nsconfig), created=START
    )
    assert manager.get_nameserver_process_info("ns")["status"] == "Died"


def test_daemon_info(manager):
    manager.daemons["d"] = SimpleNamespace(
        process=fake_process(), created=START, shared_uris={}
    )
    assert manager.get_daemon_process_info("d")["uri"] == ""

    manager.daemons["d"].shared_uris["d"] = "PYRO:d@localhost:1"
    assert manager.get_daemon_process_info("d")["uri"] == "PYRO:d@localhost:1"
    assert manager.get_daemon_process_info("other")["status"] == "Stopped"


def test_service_info_before_uri_is_published(manager):
    # Regression: raised KeyError while the daemon was still starting (#46).
    manager.daemons["d"] = SimpleNamespace(
        process=fake_process(serviceconfigs={"svc": None}), shared_uris={}
    )
    assert manager.get_service_process_info("svc") == {"daemon": "d", "uri": ""}

    manager.daemons["d"].shared_uris["svc"] = "PYRO:svc@localhost:1"
    assert manager.get_service_process_info("svc") == {
        "daemon": "d",
        "uri": "PYRO:svc@localhost:1",
    }


def test_service_info_for_unknown_service(manager):
    assert manager.get_service_process_info("svc") == {"daemon": "", "uri": ""}


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
