import pytest

from pyrolab import __version__
from pyrolab.configure import uniquify_class
from pyrolab.drivers import Instrument
from pyrolab.drivers.sample import (
    SampleAutoconnectInstrument,
    SampleService,
    SelectiveSampleService,
)
from pyrolab.server import change_behavior
from pyrolab.service import Service

###############################################################################
# Service
###############################################################################


@pytest.fixture
def service_cls():
    # set_behavior modifies the class in place, so never touch a shared one.
    return uniquify_class(Service)


@pytest.mark.parametrize("mode", ["single", "session", "percall"])
def test_set_behavior(service_cls, mode):
    service_cls.set_behavior(mode)
    assert service_cls._pyroInstancing == (mode, None)


def test_set_behavior_with_creator(service_cls):
    creator = lambda cls: cls()  # noqa: E731
    service_cls.set_behavior("session", creator)
    assert service_cls._pyroInstancing == ("session", creator)


def test_set_behavior_invalid_mode(service_cls):
    with pytest.raises(ValueError):
        service_cls.set_behavior("sometimes")


def test_set_behavior_non_string_mode(service_cls):
    with pytest.raises(TypeError):
        service_cls.set_behavior(1)


def test_set_behavior_non_callable_creator(service_cls):
    with pytest.raises(TypeError):
        service_cls.set_behavior("single", "not callable")


def test_service_ping_and_version():
    svc = Service()
    assert svc.ping() is True
    assert svc.pyrolab_version() == __version__


###############################################################################
# server.change_behavior
###############################################################################


def test_change_behavior(service_cls):
    change_behavior(service_cls, "percall")
    assert service_cls._pyroInstancing == ("percall", None)


def test_change_behavior_rejects_instances():
    with pytest.raises(TypeError):
        change_behavior(Service(), "single")


def test_change_behavior_invalid_mode(service_cls):
    with pytest.raises(ValueError):
        change_behavior(service_cls, "sometimes")


###############################################################################
# Instrument
###############################################################################


class FakeInstrument(Instrument):
    """Overrides only close(), so the base __del__ doesn't raise."""

    def close(self):
        pass


class RecordingInstrument(FakeInstrument):
    def connect(self, address=None, port=None):
        self.connected_with = {"address": address, "port": port}
        return True


def test_instrument_has_empty_autoconnect_params():
    assert FakeInstrument()._autoconnect_params == {}


def test_autoconnect_without_params_raises():
    with pytest.raises(Exception, match="No autoconnection parameters"):
        RecordingInstrument().autoconnect()


def test_autoconnect_passes_params_as_kwargs():
    inst = RecordingInstrument()
    inst._autoconnect_params = {"address": "1.2.3.4", "port": 99}
    assert inst.autoconnect() is True
    assert inst.connected_with == {"address": "1.2.3.4", "port": 99}


def test_autoconnect_uses_class_level_params():
    # This is how ServiceConfiguration delivers parameters.
    cls = uniquify_class(RecordingInstrument)
    cls._autoconnect_params = {"address": "a", "port": 1}
    inst = cls()
    inst.autoconnect()
    assert inst.connected_with == {"address": "a", "port": 1}


def test_instrument_base_methods_are_abstract():
    inst = FakeInstrument()
    with pytest.raises(NotImplementedError):
        inst.connect()
    with pytest.raises(NotImplementedError):
        Instrument.detect_devices()


###############################################################################
# Sample services
###############################################################################


def test_sample_service_methods():
    svc = SampleService()
    assert svc.echo("hi") == "SERVER RECEIVED: hi"
    assert svc.add(1, 2, 3.5) == 6.5
    assert svc.subtract(5, 7) == -2
    assert svc.multiply(2, 3, 4) == 24
    assert svc.multiply() == 1
    assert svc.divide(1, 4) == 0.25
    svc.attribute = "x"
    assert svc.attribute == "x"


def test_selective_sample_service_operations():
    svc = SelectiveSampleService([3, 1, 2])
    svc.sort()
    assert svc.items == [1, 2, 3]
    svc.sort(reverse=True)
    assert svc.items == [3, 2, 1]
    svc.set_item(0, 9)
    assert svc.item(0) == 9


def test_selective_sample_service_instances_do_not_share_items():
    # Regression: the default list was shared between instances (#73).
    a, b = SelectiveSampleService(), SelectiveSampleService()
    a.items.append(1)
    assert b.items == []


def test_selective_sample_service_copies_input():
    source = [1, 2]
    svc = SelectiveSampleService(source)
    svc.set_item(0, 99)
    assert source == [1, 2]


def test_sample_autoconnect_instrument_validates_parameters():
    inst = SampleAutoconnectInstrument()
    with pytest.raises(Exception, match="0.0.0.0"):
        inst.connect(address="1.1.1.1", port=1)
    with pytest.raises(Exception, match="9090"):
        inst.connect(address="0.0.0.0")
    with pytest.raises(Exception, match="connection"):
        inst.do_something()

    assert inst.connect(address="0.0.0.0", port=1) is True
    assert inst.do_something() is True
    inst.close()
    assert not inst.connected
