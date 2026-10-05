# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Logs
====

PyroLab's log: one file, written by one process.

The background daemon (``pyrolabd``) is the only writer of the log file. The
nameservers and daemons it runs as child processes send their records to it,
each over a pipe of its own (:py:func:`log_to_pipe` in the child,
:py:func:`collect_from_pipe` in the parent). A shared queue would be simpler,
but every process would then write through one cross-process lock, and a
child killed while holding it (stopping escalates to ``kill()`` for processes
that hang) would block logging, and with it the daemon, for good. With a
pipe per child, a killed child can only break its own pipe.

Each line of the log is one JSON object, so it can be read back reliably by
``pyrolab status``, ``pyrolab logs show``, and ``pyrolab logs export``.

Importing ``pyrolab`` configures none of this: as a library it only adds a
``NullHandler``. The ``pyrolab`` command and the daemon set up logging for
their own processes.
"""

import json
import logging
import logging.handlers
import os
import threading
import warnings
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Tuple

LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUPS = 5
LOGLEVEL_ENV_VAR = "PYROLAB_LOGLEVEL"
HUSH_DEPRECATION_ENV_VAR = "PYROLAB_HUSH_DEPRECATION"

# Marks where each run of the daemon begins, for "since it last started".
DAEMON_START_EVENT = "daemon-start"


def log_level() -> int:
    """The level from ``PYROLAB_LOGLEVEL`` (a name such as DEBUG), default INFO."""
    level = logging.getLevelName(os.environ.get(LOGLEVEL_ENV_VAR, "INFO").upper())
    return level if isinstance(level, int) else logging.INFO


###############################################################################
# Format
###############################################################################


class JsonLinesFormatter(logging.Formatter):
    """Formats each record as one line of JSON."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": datetime.fromtimestamp(record.created).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "process": record.processName,
            "pid": record.process,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        elif record.exc_text:
            entry["exception"] = record.exc_text
        if record.stack_info:
            entry["stack"] = self.formatStack(record.stack_info)
        event = getattr(record, "event", None)
        if event:
            entry["event"] = event
        return json.dumps(entry)


def format_entry(entry: dict, details: bool = True) -> str:
    """
    A log entry as readable text, with any traceback indented below it (or,
    with ``details=False``, just a note that there is one).
    """
    time = entry.get("time", "?").replace("T", " ")
    text = (
        f"{time} {entry.get('level', '?'):8s} "
        f"{entry.get('process', '?')} ({entry.get('pid', '?')}) "
        f"{entry.get('logger', '?')}: {entry.get('message', '')}"
    )
    for extra in ("exception", "stack"):
        if not entry.get(extra):
            continue
        if details:
            text += "\n" + "\n".join(
                "    " + line for line in entry[extra].splitlines()
            )
        else:
            text += " [traceback]"
    return text


###############################################################################
# Process setup
###############################################################################


def configure_process() -> None:
    """
    Process-wide settings for PyroLab's own executables (the CLI and daemon).

    Shows remote tracebacks for Pyro errors and shows deprecation warnings
    (unless ``PYROLAB_HUSH_DEPRECATION`` is set). Never called on import: a
    library must not change these for the application that imports it.
    """
    import sys

    import Pyro5.errors

    sys.excepthook = Pyro5.errors.excepthook
    action = "ignore" if HUSH_DEPRECATION_ENV_VAR in os.environ else "default"
    warnings.filterwarnings(action, category=DeprecationWarning)


def configure_cli_logging() -> None:
    """
    Logging for short-lived CLI commands: to stderr, and only if
    ``PYROLAB_LOGLEVEL`` is set. They never write the daemon's log file.
    """
    if LOGLEVEL_ENV_VAR in os.environ:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        root = logging.getLogger()
        root.addHandler(handler)
        root.setLevel(log_level())


def start_file_logging(
    logfile: Path, max_bytes: int = LOG_MAX_BYTES, backups: int = LOG_BACKUPS
) -> logging.Handler:
    """
    Make this process the writer of the log file (used by the daemon).

    Adds a rotating JSON-lines handler to the root logger, sends warnings to
    the log, and records the start of a new run. Undo with
    :py:func:`stop_file_logging`.

    Returns
    -------
    logging.Handler
        The handler that was added.
    """
    logfile.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        logfile, maxBytes=max_bytes, backupCount=backups, encoding="utf-8"
    )
    handler.setFormatter(JsonLinesFormatter())
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(log_level())
    logging.captureWarnings(True)
    # Written straight to the file, whatever the log level.
    handler.handle(
        logging.makeLogRecord(
            {
                "name": "pyrolab.pyrolabd",
                "levelno": logging.INFO,
                "levelname": "INFO",
                "msg": f"PyroLab daemon starting (pid {os.getpid()})",
                "event": DAEMON_START_EVENT,
            }
        )
    )
    return handler


def stop_file_logging(handler: logging.Handler) -> None:
    """Undo :py:func:`start_file_logging`."""
    logging.captureWarnings(False)
    logging.getLogger().removeHandler(handler)
    handler.close()


###############################################################################
# Child processes
###############################################################################


class PipeHandler(logging.Handler):
    """Sends records over a pipe to the process that writes the log."""

    def __init__(self, conn) -> None:
        super().__init__()
        self.conn = conn

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.conn.send(self.prepare(record))
        except Exception:
            self.handleError(record)

    @staticmethod
    def prepare(record: logging.LogRecord) -> dict:
        """A picklable copy of the record, with message and traceback as text."""
        data = dict(record.__dict__)
        data["msg"] = record.getMessage()
        data["args"] = None
        if record.exc_info:
            data["exc_text"] = logging.Formatter().formatException(record.exc_info)
        data["exc_info"] = None
        data.pop("message", None)
        for key, value in list(data.items()):
            if not isinstance(value, (str, int, float, bool, type(None))):
                data[key] = repr(value)
        return data


def log_to_pipe(conn) -> None:
    """
    In a child process: send all logging to the parent over ``conn``.

    Replaces any handlers inherited from the parent (with the "fork" start
    method a child inherits the parent's file handler, and must not write the
    file itself).
    """
    root = logging.getLogger()
    root.handlers = [PipeHandler(conn)]
    root.setLevel(log_level())
    logging.captureWarnings(True)


def collect_from_pipe(conn, name: str = "log-collector") -> threading.Thread:
    """
    In the parent: log every record a child sends over ``conn``.

    Runs in a daemon thread that ends when the child closes the pipe or dies
    (a message cut short by a killed child also ends it).

    Returns
    -------
    threading.Thread
        The started thread.
    """

    def collect() -> None:
        while True:
            try:
                data = conn.recv()
            except (EOFError, OSError):
                break
            except Exception:  # a torn or unreadable message
                logging.getLogger(__name__).warning(
                    "Unreadable log message from a child process; dropping its pipe",
                    exc_info=True,
                )
                break
            record = logging.makeLogRecord(data)
            logging.getLogger(record.name).handle(record)
        conn.close()

    thread = threading.Thread(target=collect, name=name, daemon=True)
    thread.start()
    return thread


###############################################################################
# Reading the log back
###############################################################################


def log_files(logfile: Path) -> List[Path]:
    """The log file and its rotated backups, oldest first."""
    backups = sorted(
        (p for p in logfile.parent.glob(logfile.name + ".*") if p.suffix[1:].isdigit()),
        key=lambda p: int(p.suffix[1:]),
        reverse=True,
    )
    return backups + ([logfile] if logfile.exists() else [])


def read_entries(files: Iterable[Path]) -> Tuple[List[dict], int]:
    """
    Read log entries from JSON-lines files.

    Returns
    -------
    entries, skipped
        Every readable entry, in file order, and the number of lines that
        couldn't be read (e.g. from an older log format).
    """
    entries, skipped = [], 0
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                skipped += 1
                continue
            if isinstance(entry, dict) and "time" in entry:
                entries.append(entry)
            else:
                skipped += 1
    return entries, skipped


def since_last_start(entries: List[dict]) -> List[dict]:
    """The entries from the daemon's most recent start onward."""
    for i in range(len(entries) - 1, -1, -1):
        if entries[i].get("event") == DAEMON_START_EVENT:
            return entries[i:]
    return entries


def at_least(entries: Iterable[dict], level: int) -> Iterator[dict]:
    """The entries at ``level`` or above."""
    for entry in entries:
        entry_level = logging.getLevelName(entry.get("level", ""))
        if isinstance(entry_level, int) and entry_level >= level:
            yield entry


def find_level(name: str) -> Optional[int]:
    """A level number from its name, or None if there is no such level."""
    level = logging.getLevelName(name.upper())
    return level if isinstance(level, int) else None
