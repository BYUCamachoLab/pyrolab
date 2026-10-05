"""
Arduino driver tests that need pyfirmata but no board.
"""

from types import SimpleNamespace

import pytest

pyfirmata = pytest.importorskip("pyfirmata")


def test_pyfirmata_command_handlers_work_on_current_python():
    # pyfirmata 1.1.0 calls inspect.getargspec, removed in Python 3.11, every
    # time a Board registers its command handlers; the driver patches that.
    import pyrolab.drivers.arduino.arduino  # noqa: F401

    board = SimpleNamespace(_command_handlers={})

    def handler(self, a, b):
        pass

    pyfirmata.Board.add_cmd_handler(board, 0x71, handler)
    assert board._command_handlers[0x71].bytes_needed == 2


def test_compat_shim_delegates_everything_else():
    from pyrolab.drivers.arduino.arduino import _InspectCompat

    shim = _InspectCompat()
    import inspect

    assert shim.signature is inspect.signature
    assert shim.getargspec(lambda x, y: None).args == ["x", "y"]


class FakePin:
    def __init__(self, values):
        self.values = list(values)
        self.mode = None

    def enable_reporting(self):
        pass

    def read(self):
        return self.values.pop(0) if self.values else None


def arduino_with_pin(values):
    from pyrolab.drivers.arduino.arduino import BaseArduinoDriver

    arduino = BaseArduinoDriver()
    arduino.board = SimpleNamespace(analog=[FakePin(values)], exit=lambda: None)
    return arduino


def test_analog_read_waits_for_the_pin_to_report():
    assert arduino_with_pin([None, None, 0.5]).analog_read(0) == 0.5


def test_analog_read_gives_up_on_a_silent_pin():
    # Regression: waited forever, hanging the daemon (#57)
    with pytest.raises(TimeoutError, match="Analog pin 0"):
        arduino_with_pin([]).analog_read(0, timeout=0.05)
