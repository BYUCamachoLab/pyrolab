"""
R&S RTO oscilloscope driver tests, with a fake VISA resource manager.
"""

from unittest.mock import MagicMock

import pytest

pytest.importorskip("pyvisa")

from pyrolab.drivers.scopes import rohdeschwarz  # noqa: E402


@pytest.fixture
def scope(monkeypatch):
    rm = MagicMock(name="ResourceManager")
    monkeypatch.setattr(rohdeschwarz.visa, "ResourceManager", lambda: rm)
    scope = rohdeschwarz.RTO()
    scope.connect(address="10.0.0.2")
    return scope, rm


def test_the_resource_manager_lives_as_long_as_the_connection(scope):
    # Regression: the ResourceManager was a local, dropped as soon as connect
    # returned (#79)
    scope, rm = scope
    assert scope._rm is rm
    assert scope.device is rm.open_resource.return_value

    scope.close()
    scope.device.close.assert_called_once()
    rm.close.assert_called_once()


def test_closing_releases_the_resource_manager_even_if_the_device_fails(scope):
    scope, rm = scope
    scope.device.close.side_effect = OSError("connection lost")
    with pytest.raises(OSError):
        scope.close()
    rm.close.assert_called_once()
