import pytest
from Pyro5.api import Proxy

from pyrolab import __version__
from pyrolab.configure import uniquify_class
from pyrolab.drivers.sample import SampleService
from pyrolab.server import Daemon, Lockable, LockableDaemon


@pytest.fixture
def lockable_daemon():
    daemon = LockableDaemon(host="localhost", port=0)
    yield daemon
    daemon.close()


def single_instance_service():
    cls = uniquify_class(SampleService)
    cls.set_behavior("single")
    return cls


###############################################################################
# Daemon
###############################################################################


def test_daemon_prepare_class_is_identity():
    assert Daemon._prepare_class(SampleService) is SampleService


def test_daemon_serves_registered_service(serve):
    daemon = serve(Daemon(host="localhost", port=0))
    uri = daemon.register(uniquify_class(SampleService))
    with Proxy(uri) as proxy:
        assert proxy.echo("hi") == "SERVER RECEIVED: hi"
        assert proxy.multiply(2, 3) == 6
        assert proxy.ping() is True
        assert proxy.pyrolab_version() == __version__


###############################################################################
# LockableDaemon bookkeeping
###############################################################################


def test_prepare_class_mixes_in_lockable():
    cls = LockableDaemon._prepare_class(SampleService)
    assert issubclass(cls, SampleService)
    assert issubclass(cls, Lockable)
    assert not issubclass(SampleService, Lockable)


def test_prepare_class_leaves_daemon_instances_alone(lockable_daemon):
    # A daemon registering itself must not be wrapped.
    assert LockableDaemon._prepare_class(lockable_daemon) is lockable_daemon


def test_lock_release_islocked(lockable_daemon):
    conn = object()
    assert not lockable_daemon._islocked("obj")
    assert lockable_daemon._lock("obj", conn, "alice") is True
    assert lockable_daemon._islocked("obj")
    assert lockable_daemon._release("obj") is True
    assert not lockable_daemon._islocked("obj")
    assert lockable_daemon._release("obj") is False


def test_lock_does_not_steal_existing_lock(lockable_daemon):
    first, second = object(), object()
    lockable_daemon._lock("obj", first, "alice")
    lockable_daemon._lock("obj", second, "bob")
    assert lockable_daemon.locked_instances["obj"] == (first, "alice")


def test_client_disconnect_releases_only_that_clients_locks(lockable_daemon):
    # Regression: clientDisconnect raised TypeError on any held lock (#45).
    alice, bob = object(), object()
    lockable_daemon._lock("a1", alice, "alice")
    lockable_daemon._lock("a2", alice, "alice")
    lockable_daemon._lock("b1", bob, "bob")

    lockable_daemon.clientDisconnect(alice)
    assert set(lockable_daemon.locked_instances) == {"b1"}


def test_client_disconnect_with_no_locks(lockable_daemon):
    lockable_daemon.clientDisconnect(object())
    assert lockable_daemon.locked_instances == {}


def test_lockable_without_daemon_is_noop():
    obj = LockableDaemon._prepare_class(SampleService)()
    assert obj.lock("me") is True
    assert obj.islocked() is False
    assert obj.unlock() is True


###############################################################################
# Locking over the wire
###############################################################################


def test_lock_blocks_other_clients(lockable_daemon, serve):
    serve(lockable_daemon)
    uri = lockable_daemon.register(single_instance_service())

    with Proxy(uri) as owner, Proxy(uri) as other:
        assert owner.lock("alice") is True
        assert owner.islocked() is True
        assert owner.echo("mine") == "SERVER RECEIVED: mine"

        with pytest.raises(ConnectionRefusedError, match="alice"):
            other.echo("let me in")

        assert owner.unlock() is True
        assert other.echo("thanks") == "SERVER RECEIVED: thanks"


def test_lock_released_when_owner_disconnects(lockable_daemon, serve, wait_for):
    # Regression for #45, end to end: a client that goes away must not leave
    # the instrument locked.
    serve(lockable_daemon)
    uri = lockable_daemon.register(single_instance_service())

    owner = Proxy(uri)
    owner.lock("alice")
    owner._pyroRelease()

    assert wait_for(lambda: not lockable_daemon.locked_instances)
    with Proxy(uri) as other:
        assert other.echo("free") == "SERVER RECEIVED: free"


def test_daemon_release_force_unlocks(lockable_daemon, serve):
    serve(lockable_daemon)
    uri = lockable_daemon.register(single_instance_service())
    daemon_uri = lockable_daemon.register(lockable_daemon)

    with Proxy(uri) as owner, Proxy(uri) as other, Proxy(daemon_uri) as admin:
        owner.lock("alice")
        with pytest.raises(ConnectionRefusedError):
            other.echo("x")

        assert admin.release(str(uri)) is True
        assert other.echo("y") == "SERVER RECEIVED: y"
