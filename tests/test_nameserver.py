import gc
import socket
import threading

import Pyro5
import Pyro5.errors
import pytest
from Pyro5.api import Proxy, locate_ns

from pyrolab.configure import NameServerConfiguration, uniquify_class
from pyrolab.drivers.sample import SampleService
from pyrolab.nameserver import start_ns, start_ns_loop
from pyrolab.server import Daemon


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


@pytest.fixture
def nameserver(serve):
    """A nameserver from ``start_ns``, served on loopback in a thread."""
    cfg = NameServerConfiguration(host="localhost", ns_port=0)
    uri, daemon, bcserver = start_ns(cfg)
    assert bcserver is None
    serve(daemon)
    return uri


def test_start_ns_returns_running_nameserver(nameserver):
    # Regression: start_ns recursed into itself (#44).
    with locate_ns(nameserver.host, nameserver.port) as ns:
        ns.ping()
        assert "Pyro.NameServer" in ns.list()


# Pyro5's SqlStorage opens connections with ``with sqlite3.connect(...)``, which
# commits but never closes them; Python 3.13+ reports each one when collected.
@pytest.mark.filterwarnings("ignore:unclosed database:ResourceWarning")
def test_start_ns_persistent_storage_survives_restart(data_dir):
    cfg = NameServerConfiguration(host="localhost", ns_port=0, storage="sql")
    cfg.set_name("persist")

    uri, daemon, _ = start_ns(cfg)
    try:
        daemon.nameserver.register("lab.thing", "PYRO:thing@localhost:1234")
    finally:
        daemon.close()

    assert (data_dir.NAMESERVER_STORAGE / "ns_persist.sql").exists()

    uri, daemon, _ = start_ns(cfg)
    try:
        assert str(daemon.nameserver.lookup("lab.thing")) == (
            "PYRO:thing@localhost:1234"
        )
    finally:
        daemon.close()
        gc.collect()  # surface Pyro5's leaked connections inside this test


def _ns_reachable(port):
    try:
        with locate_ns("localhost", port) as ns:
            ns.ping()
        return True
    except Pyro5.errors.NamingError:
        return False


def test_start_ns_loop_stops_on_loop_condition(wait_for):
    Pyro5.config.POLLTIMEOUT = 0.1
    port = free_port()
    cfg = NameServerConfiguration(host="localhost", ns_port=port)
    keep_running = threading.Event()
    keep_running.set()

    thread = threading.Thread(
        target=start_ns_loop,
        args=(cfg,),
        kwargs={"loop_condition": keep_running.is_set},
        daemon=True,
    )
    thread.start()
    try:
        assert wait_for(lambda: _ns_reachable(port))
    finally:
        keep_running.clear()
        thread.join(timeout=5)
    assert not thread.is_alive()


def test_service_lookup_through_nameserver(nameserver, serve):
    daemon = serve(Daemon(host="localhost", port=0))
    svc_uri = daemon.register(uniquify_class(SampleService))
    with locate_ns(nameserver.host, nameserver.port) as ns:
        ns.register("test.sample", svc_uri, metadata={"Echo service"})

        found = ns.lookup("test.sample")
        assert ns.list(return_metadata=True)["test.sample"][1] == {"Echo service"}

    with Proxy(found) as proxy:
        assert proxy.echo("hello") == "SERVER RECEIVED: hello"
        assert proxy.add(1, 2) == 3
