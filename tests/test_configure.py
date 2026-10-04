import Pyro5
import pytest
from pydantic import ValidationError
from yaml import load
from yaml.constructor import ConstructorError

from pyrolab import configure
from pyrolab.configure import (
    DaemonConfiguration,
    GlobalConfiguration,
    NameServerConfiguration,
    PyroLabConfiguration,
    ServiceConfiguration,
    UniqueOrAutoKeyLoader,
    export_config,
    reset_config,
    uniquify_class,
    update_config,
)
from pyrolab.drivers.sample import SampleAutoconnectInstrument, SampleService
from pyrolab.server import Daemon, LockableDaemon

###############################################################################
# YAML loading
###############################################################################


def _load(text):
    return load(text, Loader=UniqueOrAutoKeyLoader)


def test_auto_key_generates_three_word_name():
    data = _load("auto: 1\n")
    (key,) = data
    assert len(key.split("-")) == 3
    assert data[key] == 1


def test_auto_key_with_count():
    (key,) = _load("auto 5: x\n")
    assert len(key.split("-")) == 5


def test_multiple_auto_keys_get_distinct_names():
    data = _load("auto: 1\nauto 2: 2\nauto 1: 3\n")
    assert len(data) == 3


def test_auto_key_with_bad_count_is_rejected():
    with pytest.raises(ConstructorError, match="auto"):
        _load("auto many: x\n")


def test_duplicate_keys_are_rejected():
    with pytest.raises(ConstructorError, match="duplicate key"):
        _load("a: 1\na: 2\n")


def test_duplicate_keys_rejected_in_nested_mappings():
    with pytest.raises(ConstructorError, match="duplicate key"):
        _load("outer:\n  a: 1\n  a: 2\n")


###############################################################################
# PyroLabConfiguration
###############################################################################


def test_load_full_config(sample_config_file):
    cfg = PyroLabConfiguration.from_file(sample_config_file)

    assert set(cfg.nameservers) == {"local", "persistent"}
    assert cfg.nameservers["persistent"].ns_port == 9100
    assert cfg.nameservers["persistent"].storage == "sql"

    assert cfg.daemons["lockable"].classname == "LockableDaemon"
    assert cfg.daemons["lockable"].servertype == "multiplex"
    assert cfg.daemons["lockable"].nameservers == ["local"]
    assert cfg.daemons["plain"].module == "pyrolab.server"

    svc = cfg.services["sample.instrument"]
    assert svc.parameters == {"address": "0.0.0.0", "port": 1234}
    assert svc.instancemode == "single"
    assert cfg.services["sample.echo"].instancemode == "session"

    assert cfg.autolaunch.nameservers == ["local"]
    assert cfg.autolaunch.daemons == ["lockable"]


def test_empty_config_has_defaults():
    cfg = PyroLabConfiguration()
    assert cfg.nameservers == {} and cfg.daemons == {} and cfg.services == {}
    assert cfg.autolaunch.nameservers == [] and cfg.autolaunch.daemons == []


def test_yaml_round_trip(sample_config_file):
    cfg = PyroLabConfiguration.from_file(sample_config_file)
    again = PyroLabConfiguration.from_yaml(cfg.yaml())
    assert again == cfg


def test_from_file_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        PyroLabConfiguration.from_file(tmp_path / "nope.yaml")


def test_service_requires_module_and_classname():
    with pytest.raises(ValidationError):
        PyroLabConfiguration.from_yaml("services:\n  svc:\n    module: x\n")


def test_initialize_nameservers_assigns_names(sample_config_file):
    cfg = PyroLabConfiguration.from_file(sample_config_file)
    cfg.initialize_nameservers()
    assert cfg.nameservers["local"].name == "local"
    assert cfg.nameservers["persistent"].name == "persistent"


###############################################################################
# NameServerConfiguration
###############################################################################


@pytest.mark.parametrize("storage", ["memory", "sql", "dbm", "sql:/tmp/ns.db"])
def test_valid_storage(storage):
    assert NameServerConfiguration(storage=storage).storage == storage


@pytest.mark.parametrize("storage", ["", "disk", "redis:localhost"])
def test_invalid_storage(storage):
    with pytest.raises(ValidationError):
        NameServerConfiguration(storage=storage)


def test_ns_bchost_accepts_hostname():
    # Regression: was typed Optional[bool] (#48).
    assert NameServerConfiguration(ns_bchost="192.168.1.255").ns_bchost == (
        "192.168.1.255"
    )
    assert NameServerConfiguration().ns_bchost is None


def test_storage_location_memory():
    assert NameServerConfiguration().get_storage_location() == "memory"


@pytest.mark.parametrize("kind", ["sql", "dbm"])
def test_storage_location_persistent(kind, data_dir):
    cfg = NameServerConfiguration(storage=kind)
    cfg.set_name("prod")
    expected = f"{kind}:" + str(data_dir.NAMESERVER_STORAGE / f"ns_prod.{kind}")
    assert cfg.get_storage_location() == expected


def test_nameserver_update_pyro_config():
    cfg = NameServerConfiguration(host="127.0.0.1", ns_port=9555, ns_autoclean=5.0)
    applied = cfg.update_pyro_config()

    assert Pyro5.config.HOST == "127.0.0.1"
    assert Pyro5.config.NS_HOST == "127.0.0.1"  # mirrored from host
    assert Pyro5.config.NS_PORT == 9555
    assert Pyro5.config.NS_AUTOCLEAN == 5.0
    assert applied["NS_PORT"] == 9555


def test_public_host_is_resolved(monkeypatch):
    monkeypatch.setattr(configure, "get_ip", lambda: "10.9.8.7")
    NameServerConfiguration(host="public").update_pyro_config()
    assert Pyro5.config.HOST == "10.9.8.7"
    assert Pyro5.config.NS_HOST == "10.9.8.7"


def test_update_pyro_config_does_not_mutate_model(monkeypatch):
    monkeypatch.setattr(configure, "get_ip", lambda: "10.9.8.7")
    cfg = NameServerConfiguration(host="public")
    cfg.update_pyro_config()
    assert cfg.host == "public"


###############################################################################
# DaemonConfiguration
###############################################################################


def test_daemon_update_pyro_config():
    DaemonConfiguration(host="127.0.0.1", servertype="multiplex").update_pyro_config()
    assert Pyro5.config.HOST == "127.0.0.1"
    assert Pyro5.config.SERVERTYPE == "multiplex"


@pytest.mark.parametrize(
    "classname, expected", [("Daemon", Daemon), ("LockableDaemon", LockableDaemon)]
)
def test_get_daemon(classname, expected):
    assert DaemonConfiguration(classname=classname)._get_daemon() is expected


def test_get_daemon_bad_module():
    with pytest.raises(ModuleNotFoundError):
        DaemonConfiguration(module="pyrolab.nonexistent")._get_daemon()


def test_get_daemon_bad_classname():
    with pytest.raises(AttributeError):
        DaemonConfiguration(classname="NoSuchDaemon")._get_daemon()


###############################################################################
# ServiceConfiguration and uniquify_class
###############################################################################


def test_uniquify_class():
    a = uniquify_class(SampleService)
    b = uniquify_class(SampleService)
    assert a is not b
    assert issubclass(a, SampleService) and issubclass(b, SampleService)
    assert a.__name__.startswith("SampleService_")
    assert a.__name__ != b.__name__


def test_get_service_sets_behavior_and_params():
    svc = ServiceConfiguration(
        module="pyrolab.drivers.sample",
        classname="SampleAutoconnectInstrument",
        parameters={"address": "0.0.0.0", "port": 1234},
        instancemode="percall",
    )._get_service()

    assert issubclass(svc, SampleAutoconnectInstrument)
    assert svc is not SampleAutoconnectInstrument
    assert svc._pyroInstancing == ("percall", None)
    assert svc._autoconnect_params == {"address": "0.0.0.0", "port": 1234}

    inst = svc()
    assert inst.autoconnect() is True
    assert inst.connected


def test_get_service_does_not_modify_original_class():
    before = SampleAutoconnectInstrument._pyroInstancing
    ServiceConfiguration(
        module="pyrolab.drivers.sample",
        classname="SampleAutoconnectInstrument",
        parameters={"address": "0.0.0.0", "port": 1},
        instancemode="percall",
    )._get_service()
    assert SampleAutoconnectInstrument._pyroInstancing == before
    assert not hasattr(SampleAutoconnectInstrument, "_autoconnect_params")


def test_two_services_of_same_class_keep_separate_params():
    # The reason uniquify_class exists: autoconnect params are class attributes.
    def make(port):
        return ServiceConfiguration(
            module="pyrolab.drivers.sample",
            classname="SampleAutoconnectInstrument",
            parameters={"address": "0.0.0.0", "port": port},
        )._get_service()

    first, second = make(1111), make(2222)
    assert first._autoconnect_params["port"] == 1111
    assert second._autoconnect_params["port"] == 2222


def test_get_service_bad_classname():
    with pytest.raises(AttributeError):
        ServiceConfiguration(
            module="pyrolab.drivers.sample", classname="Nope"
        )._get_service()


def test_get_service_invalid_instancemode():
    with pytest.raises(ValueError):
        ServiceConfiguration(
            module="pyrolab.drivers.sample",
            classname="SampleService",
            instancemode="sometimes",
        )._get_service()


###############################################################################
# GlobalConfiguration
###############################################################################


def test_global_configuration_is_singleton(global_config):
    assert GlobalConfiguration.instance() is global_config
    with pytest.raises(RuntimeError):
        GlobalConfiguration()


def test_global_load_config(global_config, sample_config_file):
    global_config.load_config(sample_config_file)
    assert global_config.get_nameserver_config("local").name == "local"
    assert global_config.get_daemon_config("plain").host == "localhost"
    assert global_config.get_service_config("sample.echo").daemon == "plain"


def test_global_load_empty_filename_resets(global_config, sample_config_file):
    global_config.load_config(sample_config_file)
    global_config.load_config("")
    assert global_config.get_config() == PyroLabConfiguration()


def test_global_clear_all(global_config, sample_config_file):
    global_config.load_config(sample_config_file)
    global_config.clear_all()
    assert global_config.get_config().services == {}


def test_service_configs_for_daemon(global_config, sample_config_file):
    global_config.load_config(sample_config_file)
    assert set(global_config.get_service_configs_for_daemon("plain")) == {"sample.echo"}
    assert set(global_config.get_service_configs_for_daemon("lockable")) == {
        "sample.instrument"
    }
    assert global_config.get_service_configs_for_daemon("nobody") == {}


def test_global_save_config_round_trip(global_config, sample_config_file, tmp_path):
    global_config.load_config(sample_config_file)
    out = tmp_path / "saved.yaml"
    global_config.save_config(out)
    assert PyroLabConfiguration.from_file(out) == global_config.get_config()


def test_global_unknown_entity_raises(global_config):
    with pytest.raises(KeyError):
        global_config.get_daemon_config("missing")


###############################################################################
# update_config / reset_config / export_config
###############################################################################


def test_update_config_installs_user_config(data_dir, sample_config_file):
    update_config(sample_config_file)
    assert data_dir.USER_CONFIG_FILE.exists()
    assert PyroLabConfiguration.from_file(
        data_dir.USER_CONFIG_FILE
    ) == PyroLabConfiguration.from_file(sample_config_file)


def test_update_config_missing_file(data_dir, tmp_path):
    with pytest.raises(FileNotFoundError):
        update_config(tmp_path / "missing.yaml")
    assert not data_dir.USER_CONFIG_FILE.exists()


def test_update_config_invalid_leaves_existing_config(data_dir, sample_config_file):
    update_config(sample_config_file)
    before = data_dir.USER_CONFIG_FILE.read_text()

    bad = data_dir.root / "bad.yaml"
    bad.write_text("nameservers:\n  x:\n    storage: floppy\n")
    with pytest.raises(ValidationError):
        update_config(bad)
    assert data_dir.USER_CONFIG_FILE.read_text() == before


def test_reset_config(data_dir, sample_config_file):
    update_config(sample_config_file)
    reset_config()
    assert not data_dir.USER_CONFIG_FILE.exists()
    reset_config()  # no error when already absent


def test_export_config(tmp_path, sample_config_file):
    cfg = PyroLabConfiguration.from_file(sample_config_file)
    out = tmp_path / "exported.yaml"
    export_config(cfg, out)
    assert PyroLabConfiguration.from_file(out) == cfg
