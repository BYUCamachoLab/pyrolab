"""
TSL550 laser driver tests, with a fake serial port in place of the laser.
"""

import struct

import pytest

pytest.importorskip("serial")

import serial  # noqa: E402

from pyrolab.drivers.lasers.tsl550 import TSL550  # noqa: E402


class FakeSerial:
    def __init__(self, data=b"", error=None):
        self.data = data
        self.error = error

    def read(self, n):
        if self.error is not None:
            raise self.error
        chunk, self.data = self.data[:n], self.data[n:]
        return chunk

    def close(self):
        pass


@pytest.fixture
def laser(monkeypatch):
    def make(points, device):
        laser = TSL550()
        laser.device = device
        monkeypatch.setattr(laser, "wavelength_logging_number", lambda: points)
        monkeypatch.setattr(laser, "write", lambda command: None)
        monkeypatch.setattr(laser, "query", lambda command: "")
        monkeypatch.setattr("time.sleep", lambda seconds: None)
        return laser

    return make


def encode(*wavelengths_nm):
    return b"".join(struct.pack(">I", round(w * 1e4)) for w in wavelengths_nm)


def test_wavelength_logging_reads_every_point(laser):
    laser = laser(3, FakeSerial(encode(1550.0, 1550.1, 1550.2)))
    assert laser.wavelength_logging() == [1550.0, 1550.1, 1550.2]


def test_wavelength_logging_reports_where_the_data_stopped(laser):
    # Regression: a short read became an opaque "Error reading wavelength
    # data", with the original error discarded (#60)
    laser = laser(3, FakeSerial(encode(1550.0) + b"\x00\x01"))
    with pytest.raises(TimeoutError, match="after 1 of 3 points"):
        laser.wavelength_logging()


def test_wavelength_logging_keeps_the_serial_error(laser):
    error = serial.SerialException("port closed")
    laser = laser(2, FakeSerial(error=error))
    with pytest.raises(OSError) as info:
        laser.wavelength_logging()
    assert info.value.__cause__ is error
