import os
import subprocess
import sys

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


def test_pid_is_running_for_this_process():
    assert utils.pid_is_running(os.getpid())


def test_pid_is_running_for_an_exited_process():
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    assert not utils.pid_is_running(proc.pid)


def test_pid_is_running_rejects_invalid_pids():
    assert not utils.pid_is_running(0)
    assert not utils.pid_is_running(-1)


def test_atomic_write_text(tmp_path):
    target = tmp_path / "file.txt"
    utils.atomic_write_text(target, "first")
    utils.atomic_write_text(target, "second")
    assert target.read_text() == "second"
    assert [f.name for f in tmp_path.iterdir()] == ["file.txt"]


def test_atomic_write_text_failure_leaves_original(tmp_path, monkeypatch):
    target = tmp_path / "file.txt"
    target.write_text("original")

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(utils.os, "replace", boom)
    try:
        utils.atomic_write_text(target, "new")
    except OSError:
        pass
    assert target.read_text() == "original"
    assert [f.name for f in tmp_path.iterdir()] == ["file.txt"]  # no temp left
