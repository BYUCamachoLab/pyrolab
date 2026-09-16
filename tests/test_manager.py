import multiprocessing
import time
from datetime import datetime

import pytest

from pyrolab.manager import DaemonProcessGroup, NameServerProcessGroup, ProcessManager


class _RespondingProcess(multiprocessing.Process):
    """Simulates a well-behaved NameServerRunner/DaemonRunner: polls its message
    queue and exits promptly when it receives the None sentinel."""

    def __init__(self, msg_queue, msg_polling=0.05, **kwargs):
        super().__init__(**kwargs)
        self.msg_queue = msg_queue
        self.msg_polling = msg_polling

    def run(self):
        while True:
            if not self.msg_queue.empty():
                msg = self.msg_queue.get()
                if msg is None:
                    return
            time.sleep(self.msg_polling)


class _WedgedProcess(multiprocessing.Process):
    """Simulates a process stuck in a blocking call (e.g. a hardware driver read)
    that never polls its message queue, so it can only be stopped by an external
    terminate()/kill(), never by the graceful KILL sentinel."""

    def __init__(self, msg_queue, msg_polling=0.05, **kwargs):
        super().__init__(**kwargs)
        self.msg_queue = msg_queue
        self.msg_polling = msg_polling

    def run(self):
        while True:
            time.sleep(1000)


@pytest.fixture
def manager():
    pm = ProcessManager.instance()
    pm.stop_checkup_timer()
    yield pm
    pm.stop_checkup_timer()
    # Clean up anything a test left behind so state doesn't leak into other tests
    # sharing this singleton.
    for name, group in list(pm.nameservers.items()):
        group.process.kill()
        group.process.join()
        del pm.nameservers[name]
    for name, group in list(pm.daemons.items()):
        group.process.kill()
        group.process.join()
        del pm.daemons[name]


def test_shutdown_nameserver__responsive_process_confirmed_dead_and_removed(manager):
    """Regression test for #50: a normally-behaving process should still shut down
    cleanly and be removed from tracking only once it's actually dead."""
    queue = multiprocessing.Queue()
    proc = _RespondingProcess(msg_queue=queue)
    proc.start()
    manager.nameservers["test-responsive-ns"] = NameServerProcessGroup(
        proc, queue, datetime.now()
    )

    result = manager.shutdown_nameserver("test-responsive-ns")

    assert result is True
    assert "test-responsive-ns" not in manager.nameservers
    assert not proc.is_alive()
    proc.join()


def test_shutdown_nameserver__wedged_process_is_terminated_and_confirmed(manager):
    """Regression test for #50: before this fix, a process that never processes the
    KILL sentinel (e.g. wedged in a blocking hardware call) would be popped from
    tracking and reported as successfully shut down (return True) after a fixed
    sleep, while the underlying OS process -- and whatever port/hardware handle it
    held -- kept running indefinitely. It must instead be escalated to terminate(),
    confirmed dead via is_alive(), and only then removed from tracking."""
    queue = multiprocessing.Queue()
    proc = _WedgedProcess(msg_queue=queue, msg_polling=0.05)
    proc.start()
    manager.nameservers["test-wedged-ns"] = NameServerProcessGroup(
        proc, queue, datetime.now()
    )

    result = manager.shutdown_nameserver("test-wedged-ns")

    assert result is True
    assert "test-wedged-ns" not in manager.nameservers
    assert not proc.is_alive()
    proc.join()


def test_shutdown_daemon__responsive_process_confirmed_dead_and_removed(manager):
    queue = multiprocessing.Queue()
    proc = _RespondingProcess(msg_queue=queue)
    proc.start()
    manager.daemons["test-responsive-daemon"] = DaemonProcessGroup(
        proc, queue, datetime.now(), {}
    )

    result = manager.shutdown_daemon("test-responsive-daemon")

    assert result is True
    assert "test-responsive-daemon" not in manager.daemons
    assert not proc.is_alive()
    proc.join()


def test_shutdown_daemon__wedged_process_is_terminated_and_confirmed(manager):
    queue = multiprocessing.Queue()
    proc = _WedgedProcess(msg_queue=queue, msg_polling=0.05)
    proc.start()
    manager.daemons["test-wedged-daemon"] = DaemonProcessGroup(
        proc, queue, datetime.now(), {}
    )

    result = manager.shutdown_daemon("test-wedged-daemon")

    assert result is True
    assert "test-wedged-daemon" not in manager.daemons
    assert not proc.is_alive()
    proc.join()
