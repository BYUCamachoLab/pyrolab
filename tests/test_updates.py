import json
import os
import subprocess
import sys
import textwrap

import pytest
import requests

from pyrolab import updates

DAY = updates.CHECK_INTERVAL
NOW = 1_800_000_000.0


@pytest.fixture
def pypi(monkeypatch):
    """
    Enable the check and fake PyPI. Set ``.latest`` to a version string, or
    to an exception instance to make the request fail; ``.calls`` counts
    requests.
    """
    monkeypatch.delenv(updates.DISABLE_ENV_VAR)

    class FakePyPI:
        latest = "9.9.9"
        calls = 0

    def fetch():
        FakePyPI.calls += 1
        if isinstance(FakePyPI.latest, Exception):
            raise FakePyPI.latest
        return FakePyPI.latest

    monkeypatch.setattr(updates, "fetch_latest_version", fetch)
    return FakePyPI


@pytest.fixture
def cache(tmp_path):
    return tmp_path / "update_check.json"


def test_reports_newer_version(pypi, cache):
    assert updates.check_for_update("1.0.0", cache, now=NOW) == "9.9.9"
    assert json.loads(cache.read_text()) == {"checked": NOW, "latest": "9.9.9"}


@pytest.mark.parametrize("current", ["9.9.9", "10.0.0"])
def test_silent_when_up_to_date(pypi, cache, current):
    assert updates.check_for_update(current, cache, now=NOW) is None


def test_checks_at_most_once_per_interval(pypi, cache):
    updates.check_for_update("1.0.0", cache, now=NOW)
    assert updates.check_for_update("1.0.0", cache, now=NOW + DAY - 1) is None
    assert pypi.calls == 1

    assert updates.check_for_update("1.0.0", cache, now=NOW + DAY) == "9.9.9"
    assert pypi.calls == 2


def test_failed_check_is_cached_too(pypi, cache):
    # An offline machine must not wait for the timeout on every command.
    pypi.latest = requests.ConnectionError("no route to host")
    assert updates.check_for_update("1.0.0", cache, now=NOW) is None
    assert json.loads(cache.read_text()) == {"checked": NOW, "latest": None}

    assert updates.check_for_update("1.0.0", cache, now=NOW + 60) is None
    assert pypi.calls == 1


def test_any_exception_is_swallowed(pypi, cache):
    pypi.latest = KeyError("info")  # e.g. unexpected JSON from PyPI
    assert updates.check_for_update("1.0.0", cache, now=NOW) is None


@pytest.mark.parametrize("contents", ["", "not json", "[]", '{"other": 1}'])
def test_unreadable_cache_triggers_a_check(pypi, cache, contents):
    cache.write_text(contents)
    assert updates.check_for_update("1.0.0", cache, now=NOW) == "9.9.9"


def test_clock_moved_backwards_triggers_a_check(pypi, cache):
    cache.write_text(json.dumps({"checked": NOW + DAY, "latest": None}))
    assert updates.check_for_update("1.0.0", cache, now=NOW) == "9.9.9"


def test_unwritable_cache_still_reports(pypi, tmp_path):
    cache = tmp_path / "missing-dir" / "update_check.json"
    assert updates.check_for_update("1.0.0", cache, now=NOW) == "9.9.9"


def test_unparseable_version_is_ignored(pypi, cache):
    pypi.latest = "not-a-version"
    assert updates.check_for_update("1.0.0", cache, now=NOW) is None


def test_disabled_by_environment_variable(pypi, cache, monkeypatch):
    monkeypatch.setenv(updates.DISABLE_ENV_VAR, "1")
    assert updates.check_for_update("1.0.0", cache, now=NOW) is None
    assert pypi.calls == 0
    assert not cache.exists()


def test_fetch_uses_a_timeout(monkeypatch):
    # Regression: the request had no timeout and could hang for minutes (#62).
    seen = {}

    class Response:
        def raise_for_status(self):
            seen["checked_status"] = True

        def json(self):
            return {"info": {"version": "1.2.3"}}

    def get(url, **kwargs):
        seen.update(url=url, **kwargs)
        return Response()

    monkeypatch.setattr(updates.requests, "get", get)
    assert updates.fetch_latest_version() == "1.2.3"
    assert seen["timeout"] == updates.TIMEOUT
    assert seen["checked_status"]


def test_importing_pyrolab_makes_no_network_requests():
    # Regression: `import pyrolab` contacted PyPI on every import (#62). Run in
    # a fresh interpreter, since this one has already imported pyrolab. Any
    # request to a named host needs a DNS lookup, so intercept those (requests
    # opens its sockets through urllib3, bypassing socket.create_connection).
    # Lookups are recorded rather than raised, because the old code swallowed
    # every exception from its check.
    code = textwrap.dedent(
        """
        import socket, sys

        lookups = []

        def record(host, *args, **kwargs):
            lookups.append(host)
            raise OSError("blocked by test")

        socket.getaddrinfo = record
        import pyrolab, pyrolab.api, pyrolab.cli
        sys.exit(f"hostname lookups on import: {lookups}" if lookups else 0)
        """
    )
    env = dict(os.environ)
    env.pop(updates.DISABLE_ENV_VAR, None)
    result = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
