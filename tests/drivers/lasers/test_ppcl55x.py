"""
PPCL55x laser driver tests, with a fake serial port in place of the laser.
"""

import threading

import pytest

pytest.importorskip("serial")

import serial  # noqa: E402
from Pyro5 import serializers  # noqa: E402

from pyrolab.drivers.lasers import ppcl55x  # noqa: E402


class FakeSerial:
    """
    Answers each message with the next queued reply: bytes to deliver, None to
    stay silent (a timeout), or an exception to raise from ``read``.
    """

    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []
        self.buffer = b""
        self.read_error = None
        self.is_open = True

    def flush(self):
        pass

    def write(self, data):
        self.sent.append(data)
        reply = self.replies.pop(0) if self.replies else None
        if isinstance(reply, Exception):
            self.buffer, self.read_error = b"\x00" * 4, reply
        elif reply is not None:
            self.buffer = reply

    def inWaiting(self):
        return len(self.buffer)

    def read(self, n):
        if self.read_error is not None:
            error, self.read_error = self.read_error, None
            raise error
        data, self.buffer = self.buffer[:n], self.buffer[n:]
        return data

    def close(self):
        self.is_open = False


def reply(register=0, data=0, corrupt=False):
    """A reply from the laser, with a valid checksum unless ``corrupt``."""
    message = [0, register, data >> 8, data & 0xFF]
    message[0] |= ppcl55x.PPCL55xBase._checksum(None, message) << 4
    if corrupt:
        message[3] ^= 0x01
    return bytes(message)


@pytest.fixture
def laser(monkeypatch):
    """Returns a function making a connected laser that gives ``replies``."""
    monkeypatch.setattr(ppcl55x, "REPLY_TIMEOUT", 0.05)

    def make(*replies):
        device = FakeSerial(replies)
        monkeypatch.setattr(ppcl55x.serial, "Serial", lambda *a, **k: device)
        laser = ppcl55x.PPCL550()
        laser.connect(port="COM1")
        return laser, device

    return make


def test_a_reply_is_returned(laser):
    laser, _ = laser(reply(ppcl55x.REG_Oop, 1234))
    message = laser._communicate(ppcl55x.REG_Oop, 0, 0)
    assert (message[2] << 8) | message[3] == 1234


def test_no_reply_raises_timeout_error(laser):
    # Regression: a timeout returned (0xFF, 0xFF, 0xFF, 0xFF), which callers
    # couldn't tell from data (#58)
    laser, _ = laser(None)
    with pytest.raises(TimeoutError):
        laser._communicate(ppcl55x.REG_Oop, 0, 0)


def test_a_bad_checksum_raises_os_error(laser):
    # Regression: raised CommunicationError, which was never imported, so it
    # became a NameError (#88)
    laser, _ = laser(reply(corrupt=True))
    with pytest.raises(OSError, match="checksum"):
        laser._communicate(ppcl55x.REG_Oop, 0, 0)


def test_a_failed_read_keeps_the_serial_error(laser):
    # Regression: a bare except replaced the serial error (#60)
    error = serial.SerialException(
        "device reports readiness to read but returned no data"
    )
    laser, _ = laser(error)
    with pytest.raises(OSError) as info:
        laser._communicate(ppcl55x.REG_Oop, 0, 0)
    assert info.value.__cause__ is error


def test_a_failed_exchange_does_not_block_the_next(laser):
    # Regression: a failed exchange never gave up its place in the queue, so
    # every later call spun forever.
    laser, _ = laser(None, reply(ppcl55x.REG_Oop, 7))
    with pytest.raises(TimeoutError):
        laser._communicate(ppcl55x.REG_Oop, 0, 0)

    result = []
    worker = threading.Thread(
        target=lambda: result.append(laser._communicate(ppcl55x.REG_Oop, 0, 0)),
        daemon=True,
    )
    worker.start()
    worker.join(timeout=5)
    assert not worker.is_alive(), "the next exchange hung"
    assert result[0][3] == 7


def test_concurrent_exchanges_are_not_interleaved(laser):
    laser, device = laser(*[reply(ppcl55x.REG_Oop, n) for n in range(40)])
    original_write = device.write
    inside = []

    def write(data):
        inside.append(1)
        assert len(inside) == 1, "two exchanges overlapped"
        original_write(data)

    original_read = device.read

    def read(n):
        data = original_read(n)
        inside.pop()
        return data

    device.write, device.read = write, read
    errors = []

    def talk():
        try:
            for _ in range(10):
                laser._communicate(ppcl55x.REG_Oop, 0, 0)
        except Exception as e:
            errors.append(e)

    workers = [threading.Thread(target=talk) for _ in range(4)]
    for w in workers:
        w.start()
    for w in workers:
        w.join(timeout=10)
    assert not errors


def test_turning_on_tolerates_unanswered_no_ops(laser):
    # The no-ops after enabling the laser are only a delay.
    laser, device = laser(reply(ppcl55x.REG_Resena), *[None] * 10)
    laser.on()
    assert laser.is_on
    assert len(device.sent) == 11


def test_turning_on_an_unresponsive_laser_fails(laser):
    laser, _ = laser(None)
    with pytest.raises(TimeoutError):
        laser.on()


@pytest.mark.parametrize("error", [TimeoutError("late"), OSError("bad checksum")])
def test_the_errors_reach_pyro_clients_intact(error):
    # Pyro can only rebuild built-in (and Pyro's own) exception classes on
    # the client; anything else arrives as a SerializeError.
    serializer = serializers.serializers["serpent"]
    received = serializer.loads(serializer.dumps(error))
    assert type(received) is type(error)
    assert received.args == error.args
