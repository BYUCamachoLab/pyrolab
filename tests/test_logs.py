"""
The single log file (#25, #64) and reading it back (#71, #36).

The child-process tests start real processes, since the point is how logging
behaves across them; each is bounded by timeouts.
"""

import json
import logging
import multiprocessing as mp
import pickle
import time

import pytest

from pyrolab import logs

###############################################################################
# Format and reading
###############################################################################


def make_record(msg="hello %s", args=("world",), level=logging.INFO, **extra):
    record = logging.LogRecord("pyrolab.test", level, __file__, 1, msg, args, None)
    record.__dict__.update(extra)
    return record


def test_json_lines_formatter():
    record = make_record(event="daemon-start")
    entry = json.loads(logs.JsonLinesFormatter().format(record))
    assert entry["message"] == "hello world"
    assert entry["level"] == "INFO"
    assert entry["logger"] == "pyrolab.test"
    assert entry["event"] == "daemon-start"
    assert {"time", "process", "pid"} <= set(entry)


def test_json_lines_formatter_includes_traceback():
    try:
        1 / 0
    except ZeroDivisionError:
        record = make_record()
        record.exc_info = __import__("sys").exc_info()
    entry = json.loads(logs.JsonLinesFormatter().format(record))
    assert "ZeroDivisionError" in entry["exception"]
    assert "\n" not in logs.JsonLinesFormatter().format(record)  # one line


def test_format_entry_indents_traceback():
    text = logs.format_entry(
        {
            "time": "2026-10-05T10:00:00.000",
            "level": "ERROR",
            "process": "lab",
            "pid": 7,
            "logger": "pyrolab.manager",
            "message": "boom",
            "exception": "Traceback:\n  line\nValueError",
        }
    )
    assert text.splitlines() == [
        "2026-10-05 10:00:00.000 ERROR    lab (7) pyrolab.manager: boom",
        "    Traceback:",
        "      line",
        "    ValueError",
    ]


def test_read_entries_skips_unreadable_lines(tmp_path):
    # Regression: one malformed entry crashed `logs export` (#71).
    path = tmp_path / "pyrolab.log"
    path.write_text(
        '{"time": "t1", "message": "a"}\n'
        "[2026-01-01 10:00:00.000] INFO old plain-text format\n"
        "Traceback (most recent call last):\n"
        "\n"
        '{"no": "time"}\n'
        '{"time": "t2", "message": "b"}\n'
    )
    entries, skipped = logs.read_entries([path])
    assert [e["message"] for e in entries] == ["a", "b"]
    assert skipped == 3


def test_since_last_start_and_levels():
    entries = [
        {"time": "1", "level": "ERROR", "message": "old run"},
        {"time": "2", "level": "INFO", "event": logs.DAEMON_START_EVENT},
        {"time": "3", "level": "INFO", "message": "fine"},
        {"time": "4", "level": "WARNING", "message": "hmm"},
    ]
    recent = logs.since_last_start(entries)
    assert [e["time"] for e in recent] == ["2", "3", "4"]
    assert [e["time"] for e in logs.at_least(recent, logging.WARNING)] == ["4"]
    # No start marker (e.g. rotated away): everything counts.
    assert logs.since_last_start(entries[2:]) == entries[2:]


###############################################################################
# The daemon's log file
###############################################################################


@pytest.fixture
def file_logging(tmp_path):
    """Make this process the log writer (as the daemon is), then undo it."""
    logfile = tmp_path / "logs" / "pyrolab.log"
    handlers = []

    def start(**kwargs):
        handlers.append(logs.start_file_logging(logfile, **kwargs))
        return logfile

    yield start
    for handler in handlers:
        logs.stop_file_logging(handler)


def test_file_logging_writes_json_lines_with_start_marker(file_logging):
    logfile = file_logging()
    logging.getLogger("pyrolab.test").warning("careful")
    entries, skipped = logs.read_entries(logs.log_files(logfile))
    assert skipped == 0
    assert entries[0]["event"] == logs.DAEMON_START_EVENT
    assert entries[-1]["message"] == "careful"


def test_stop_file_logging_removes_handler(tmp_path):
    before = list(logging.getLogger().handlers)
    handler = logs.start_file_logging(tmp_path / "pyrolab.log")
    logs.stop_file_logging(handler)
    assert logging.getLogger().handlers == before


def test_rotation_keeps_entries_in_order(file_logging):
    # Regression: per-PID files with 30 KB rotation threw history away (#64).
    logfile = file_logging(max_bytes=2000, backups=50)
    log = logging.getLogger("pyrolab.test")
    for i in range(200):
        log.warning("message %03d", i)
    files = logs.log_files(logfile)
    assert len(files) > 3
    assert files[-1] == logfile  # oldest first, current last
    entries, _ = logs.read_entries(files)
    numbered = [e["message"] for e in entries if e["message"].startswith("message")]
    assert numbered == [f"message {i:03d}" for i in range(200)]


###############################################################################
# Child processes
###############################################################################


def test_log_to_pipe_replaces_inherited_handlers():
    # With "fork", a child inherits the daemon's file handler and must not
    # write the file itself.
    root = logging.getLogger()
    saved = list(root.handlers), root.level
    a, b = mp.Pipe(duplex=False)
    try:
        root.addHandler(logging.NullHandler())
        logs.log_to_pipe(b)
        assert [type(h) for h in root.handlers] == [logs.PipeHandler]
    finally:
        root.handlers[:] = saved[0]
        root.setLevel(saved[1])
        logging.captureWarnings(False)
        a.close()
        b.close()


def test_prepared_records_are_picklable():
    try:
        raise ValueError("bad")
    except ValueError:
        record = make_record(unpicklable=lambda: None)
        record.exc_info = __import__("sys").exc_info()
    data = logs.PipeHandler.prepare(record)
    restored = logging.makeLogRecord(pickle.loads(pickle.dumps(data)))
    assert restored.getMessage() == "hello world"
    assert "ValueError: bad" in restored.exc_text


def _child_logs(conn, count):
    logs.log_to_pipe(conn)
    log = logging.getLogger("pyrolab.child")
    for i in range(count):
        log.info("child message %d", i)
    try:
        1 / 0
    except ZeroDivisionError:
        log.exception("child failed")


def _child_spams(conn):
    logs.log_to_pipe(conn)
    while True:
        logging.getLogger("pyrolab.child").info("x" * 2000)


def _start_child(target, *args, name):
    recv, send = mp.Pipe(duplex=False)
    proc = mp.Process(target=target, args=(send, *args), name=name, daemon=True)
    proc.start()
    send.close()
    collector = logs.collect_from_pipe(
        recv, name=f"log-{name}", alive=proc.is_alive, poll_interval=0.1
    )
    return proc, collector


@pytest.fixture(params=["spawn", "fork"])
def start_method(request):
    if request.param not in mp.get_all_start_methods():
        pytest.skip(f"no {request.param} start method on this platform")
    return mp.get_context(request.param)


def test_children_log_to_one_file_through_their_pipes(
    file_logging, start_method, monkeypatch
):
    # Regression: every process wrote its own file, uncoordinated (#25, #64).
    monkeypatch.setattr(mp, "Process", start_method.Process)
    monkeypatch.setattr(mp, "Pipe", start_method.Pipe)
    logfile = file_logging()
    children = [_start_child(_child_logs, 100, name=f"lab-{i}") for i in range(2)]
    for proc, collector in children:
        proc.join(30)
        collector.join(10)
        assert proc.exitcode == 0
        assert not collector.is_alive()

    entries, skipped = logs.read_entries(logs.log_files(logfile))
    assert skipped == 0
    for i in range(2):
        mine = [e for e in entries if e["process"] == f"lab-{i}"]
        assert len(mine) == 101
        assert "ZeroDivisionError" in mine[-1]["exception"]


def test_killed_child_cannot_block_logging(file_logging, start_method, monkeypatch):
    # The reason for a pipe per child rather than one shared queue: a child
    # killed mid-write (as stopping does with hung processes) must not leave a
    # lock held that blocks every other process's logging.
    monkeypatch.setattr(mp, "Process", start_method.Process)
    monkeypatch.setattr(mp, "Pipe", start_method.Pipe)
    logfile = file_logging()
    for _ in range(3):
        victims = [_start_child(_child_spams, name="victim") for _ in range(3)]
        time.sleep(0.3)
        for proc, collector in victims:
            proc.kill()
            proc.join(10)
            collector.join(10)
            assert not collector.is_alive()

    survivor, collector = _start_child(_child_logs, 20, name="survivor")
    survivor.join(30)
    collector.join(10)
    assert survivor.exitcode == 0
    logging.getLogger("pyrolab.test").warning("parent still logging")

    entries, _ = logs.read_entries(logs.log_files(logfile))
    assert len([e for e in entries if e["process"] == "survivor"]) == 21
    assert entries[-1]["message"] == "parent still logging"


def _never_starts_logging(conn):
    time.sleep(60)  # e.g. killed before it gets going


def test_collector_ends_when_child_dies_without_closing_pipe():
    # On Windows a child killed while still starting never takes its end of
    # the pipe over from the parent, so the pipe never reports closed; the
    # collector must notice the child died instead of waiting forever.
    recv, send = mp.Pipe(duplex=False)
    state = {"alive": True}
    collector = logs.collect_from_pipe(
        recv, alive=lambda: state["alive"], poll_interval=0.05
    )
    send.send(logs.PipeHandler.prepare(make_record("last words", ())))
    state["alive"] = False  # dies, but `send` (the stranded end) stays open
    collector.join(5)
    assert not collector.is_alive()
    send.close()


def test_collector_reads_everything_before_stopping(caplog):
    recv, send = mp.Pipe(duplex=False)
    for i in range(50):
        send.send(logs.PipeHandler.prepare(make_record("record %d", (i,))))
    with caplog.at_level(logging.INFO, logger="pyrolab.test"):
        collector = logs.collect_from_pipe(
            recv, alive=lambda: False, poll_interval=0.05
        )
        collector.join(5)
    assert not collector.is_alive()
    assert [r.getMessage() for r in caplog.records][-1] == "record 49"
    send.close()


###############################################################################
# Process setup
###############################################################################


def test_cli_logging_only_when_requested(monkeypatch):
    root = logging.getLogger()
    saved = list(root.handlers), root.level
    try:
        monkeypatch.delenv(logs.LOGLEVEL_ENV_VAR, raising=False)
        logs.configure_cli_logging()
        assert root.handlers == saved[0]

        monkeypatch.setenv(logs.LOGLEVEL_ENV_VAR, "debug")
        logs.configure_cli_logging()
        assert isinstance(root.handlers[-1], logging.StreamHandler)
        assert root.level == logging.DEBUG
    finally:
        root.handlers[:] = saved[0]
        root.setLevel(saved[1])


@pytest.mark.parametrize("value, level", [("WARNING", 30), ("debug", 10), ("nope", 20)])
def test_log_level_from_environment(monkeypatch, value, level):
    monkeypatch.setenv(logs.LOGLEVEL_ENV_VAR, value)
    assert logs.log_level() == level
