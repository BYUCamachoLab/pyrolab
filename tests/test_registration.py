"""
Nameserver registration (#52, #53) and the runners' own run() loops.

Addresses are 127.0.0.1 rather than "localhost": on CI runners "localhost"
also resolves to ::1, so a port held on IPv4 can still be bound on IPv6, and a
"refused" or "silent" endpoint on one family is a different one on the other.

Nameservers are real, served on loopback in threads. Runners' run() methods
are called in a thread of this process (not spawned), so their behaviour can
be observed directly.
"""

import logging
import queue
import socket
import threading
import time

import Pyro5
import pytest
from Pyro5.api import Proxy

from pyrolab import manager as mgr
from pyrolab.configure import (
    DaemonConfiguration,
    NameServerConfiguration,
    ServiceConfiguration,
)
from pyrolab.manager import DaemonRunner, NameServerRunner, Registrations
from pyrolab.nameserver import start_ns


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def live_ns(serve):
    """A running nameserver; returns (config, its NameServer object)."""
    cfg = NameServerConfiguration(host="127.0.0.1", ns_port=0)
    uri, daemon, _ = start_ns(cfg)
    serve(daemon)
    return NameServerConfiguration(
        host="127.0.0.1", ns_port=uri.port
    ), daemon.nameserver


@pytest.fixture
def dead_ns():
    """Configuration for a nameserver that refuses connections."""
    return NameServerConfiguration(host="127.0.0.1", ns_port=free_port())


@pytest.fixture
def silent_ns():
    """A port that accepts connections but never answers them."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen(5)
        yield NameServerConfiguration(host="127.0.0.1", ns_port=s.getsockname()[1])


URI = "PYRO:obj_1@127.0.0.1:1234"


###############################################################################
# Registrations
###############################################################################


def test_register_with_a_live_nameserver(live_ns):
    cfg, ns = live_ns
    regs = Registrations({"live": cfg})
    regs.add("live", "lab.thing", URI, {"A thing"})

    assert regs.register_pending() is True
    assert str(ns.lookup("lab.thing")) == URI
    assert ns.list(return_metadata=True)["lab.thing"][1] == {"A thing"}


def test_unreachable_nameserver_does_not_block_the_others(live_ns, dead_ns):
    # Regression: one failed registration killed the whole daemon (#52).
    cfg, ns = live_ns
    regs = Registrations({"live": cfg, "dead": dead_ns})
    regs.add("dead", "lab.a", URI)
    regs.add("live", "lab.b", URI)

    assert regs.register_pending() is False
    assert "lab.b" in ns.list()
    assert set(regs.pending) == {"dead"}


def test_pending_registration_succeeds_once_nameserver_appears(serve):
    port = free_port()
    regs = Registrations({"later": NameServerConfiguration(ns_port=port)})
    regs.add("later", "lab.thing", URI)
    assert regs.register_pending() is False

    _, daemon, _ = start_ns(NameServerConfiguration(host="127.0.0.1", ns_port=port))
    serve(daemon)
    assert regs.register_pending() is True
    assert "lab.thing" in daemon.nameserver.list()


def test_unresponsive_nameserver_times_out(silent_ns, monkeypatch):
    # Pyro's default is to wait forever.
    monkeypatch.setattr(mgr, "NAMESERVER_TIMEOUT", 0.3)
    regs = Registrations({"silent": silent_ns})
    regs.add("silent", "lab.thing", URI)

    began = time.monotonic()
    assert regs.register_pending() is False
    assert time.monotonic() - began < 3


def test_repeated_failures_warn_only_once(dead_ns, caplog):
    regs = Registrations({"dead": dead_ns})
    regs.add("dead", "lab.thing", URI)
    with caplog.at_level(logging.DEBUG, logger="pyrolab.manager"):
        for _ in range(3):
            regs.register_pending()
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "retrying every" in warnings[0].getMessage()


def test_proxies_are_always_released(live_ns, dead_ns, monkeypatch):
    # Regression: every registration leaked a nameserver proxy (#53).
    created, released = [], []

    class CountingProxy(Proxy):
        def __init__(self, uri):
            super().__init__(uri)
            created.append(self)

        def _pyroRelease(self):
            released.append(self)
            super()._pyroRelease()

    monkeypatch.setattr(mgr, "Proxy", CountingProxy)
    cfg, _ = live_ns
    regs = Registrations({"live": cfg, "dead": dead_ns})
    for name in ("a", "b", "c"):
        regs.add("live", name, URI)
        regs.add("dead", name, URI)
    regs.register_pending()
    regs.remove_all()

    # One proxy per nameserver per pass, each released, even on failure.
    assert len(created) == 3  # live + dead, then live again to remove
    assert len(released) == len(created)


def test_remove_all(live_ns):
    cfg, ns = live_ns
    regs = Registrations({"live": cfg})
    regs.add("live", "lab.thing", URI)
    regs.register_pending()
    regs.remove_all()
    assert "lab.thing" not in ns.list()


def test_remove_registrations_tolerates_unreachable(dead_ns, caplog):
    mgr.remove_registrations({"dead": dead_ns}, {"dead": ["lab.thing"]})
    assert "Could not remove lab.thing" in caplog.text


###############################################################################
# DaemonRunner.run() and NameServerRunner.run()
###############################################################################


@pytest.fixture
def fast_polling():
    Pyro5.config.POLLTIMEOUT = 0.1


def run_in_thread(runner):
    errors = []

    def target():
        try:
            runner.run()
        except BaseException as e:
            errors.append(e)

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    return thread, errors


def test_daemon_survives_unreachable_nameserver(
    data_dir, live_ns, dead_ns, fast_polling, wait_for
):
    # Regression for #52, end to end: a service registered with one reachable
    # and one unreachable nameserver is still served, and registered where
    # possible.
    cfg, ns = live_ns
    data_dir.RUNTIME_CONFIG.write_text(
        f"nameservers:\n"
        f"  live: {{host: 127.0.0.1, ns_port: {cfg.ns_port}}}\n"
        f"  dead: {{host: 127.0.0.1, ns_port: {dead_ns.ns_port}}}\n"
    )
    state, uris, msgs = {}, {}, queue.Queue()
    runner = DaemonRunner(
        name="lab",
        daemonconfig=DaemonConfiguration(host="127.0.0.1"),
        serviceconfigs={
            "sample.echo": ServiceConfiguration(
                module="pyrolab.drivers.sample",
                classname="SampleService",
                description="Echo",
                nameservers=["dead", "live"],
            )
        },
        msg_queue=msgs,
        shared_uris=uris,
        msg_polling=0.05,
        shared_state=state,
    )
    thread, errors = run_in_thread(runner)

    assert wait_for(lambda: state.get("ready"))
    assert wait_for(lambda: "sample.echo" in ns.list())
    with Proxy(uris["sample.echo"]) as proxy:
        assert proxy.echo("hi") == "SERVER RECEIVED: hi"

    msgs.put(None)
    thread.join(timeout=10)
    assert not thread.is_alive()
    assert errors == []
    assert "sample.echo" not in ns.list()  # deregistered on the way out


def test_daemon_runner_reports_startup_error(data_dir):
    state = {}
    runner = DaemonRunner(
        name="lab",
        daemonconfig=DaemonConfiguration(host="127.0.0.1"),
        serviceconfigs={
            "broken": ServiceConfiguration(module="no.such.module", classname="X")
        },
        msg_queue=queue.Queue(),
        shared_uris={},
        shared_state=state,
    )
    with pytest.raises(ModuleNotFoundError):
        runner.run()
    assert state["error"] == "ModuleNotFoundError: No module named 'no'"
    assert not state.get("ready")


def test_nameserver_runner_reports_ready_and_stops(fast_polling, wait_for):
    state, msgs = {}, queue.Queue()
    port = free_port()
    runner = NameServerRunner(
        name="ns",
        nsconfig=NameServerConfiguration(host="127.0.0.1", ns_port=port),
        msg_queue=msgs,
        msg_polling=0.05,
        shared_state=state,
    )
    thread, errors = run_in_thread(runner)

    assert wait_for(lambda: state.get("ready"))
    with Proxy(f"PYRO:Pyro.NameServer@127.0.0.1:{port}") as ns:
        ns.ping()

    msgs.put(None)
    thread.join(timeout=10)
    assert not thread.is_alive()
    assert errors == []


def test_nameserver_runner_reports_startup_error(fast_polling):
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen(1)
        state, msgs = {}, queue.Queue()
        runner = NameServerRunner(
            name="ns",
            nsconfig=NameServerConfiguration(
                host="127.0.0.1", ns_port=taken.getsockname()[1]
            ),
            msg_queue=msgs,
            msg_polling=0.05,
            shared_state=state,
        )
        # In a thread with a bounded wait: if the port were somehow free,
        # run() would serve forever instead of failing.
        thread, errors = run_in_thread(runner)
        thread.join(timeout=10)
        if thread.is_alive():
            msgs.put(None)
            thread.join(timeout=10)
            pytest.fail("nameserver started on a port that was already in use")
    assert errors, "run() should have raised"
    assert state["error"]  # e.g. "CommunicationError: ... address in use"
    assert not state.get("ready")
