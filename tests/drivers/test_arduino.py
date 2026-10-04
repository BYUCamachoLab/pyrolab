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
