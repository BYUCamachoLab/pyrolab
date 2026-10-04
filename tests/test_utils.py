import pyrolab
from pyrolab import utils


def _wordlist():
    from importlib.resources import files

    return set((files(pyrolab) / "data" / "wordlist.txt").read_text().splitlines())


def test_generate_random_name_default_is_three_words():
    words = utils.generate_random_name().split("-")
    assert len(words) == 3
    assert set(words) <= _wordlist()


def test_generate_random_name_count():
    assert len(utils.generate_random_name(5).split("-")) == 5
    assert len(utils.generate_random_name(1).split("-")) == 1


def test_generate_random_name_varies():
    names = {utils.generate_random_name(4) for _ in range(20)}
    assert len(names) > 1


def test_get_ip_returns_socket_address(monkeypatch):
    calls = {}

    class FakeSocket:
        def __init__(self, *args):
            pass

        def connect(self, addr):
            calls["connect"] = addr

        def getsockname(self):
            return ("10.1.2.3", 54321)

        def close(self):
            calls["closed"] = True

    monkeypatch.setattr(utils.socket, "socket", FakeSocket)
    ip = utils.get_ip()
    assert ip == "10.1.2.3"
    assert calls["closed"]
