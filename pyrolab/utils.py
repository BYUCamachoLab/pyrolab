# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Utils
=====

Convenience functions for working with the pyrolab package.
"""

import logging
import os
import secrets
import socket
import sys

try:
    import importlib.resources as pkg_resources
except ImportError:
    import pkg_resources

import pyrolab

log = logging.getLogger(__name__)


def get_ip() -> str:
    """
    This machine's best-guess address for other machines to reach it.

    Used for ``host: public``: daemons and nameservers listen on this address,
    and it goes into the URIs they publish, so it must be one the *clients* can
    reach. The guess is the address of the interface that would route to the
    internet (no traffic is sent). On a machine with several networks that may
    not be the clients' network; set ``host`` to the right address instead.

    Falls back, with a warning, to the address this machine's hostname resolves
    to, then to 127.0.0.1, rather than failing on a network with no route
    outside.

    Returns
    -------
    str
        An IPv4 address.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))  # UDP: picks a route, sends nothing
            return s.getsockname()[0]
    except OSError as e:
        reason = e

    try:
        ip = socket.gethostbyname(socket.gethostname())
    except OSError:
        ip = None
    if ip and not ip.startswith("127."):
        log.warning(
            "No route to the internet to find this machine's address (%s); using "
            "%s, which its hostname resolves to. If clients can't connect, set "
            "'host' to the address they should use instead of 'public'.",
            reason,
            ip,
        )
        return ip

    log.warning(
        "Could not find this machine's network address (%s); using 127.0.0.1, "
        "which only clients on this machine can reach. Set 'host' to the "
        "address clients should use instead of 'public'.",
        reason,
    )
    return "127.0.0.1"


def generate_random_name(count: int = 3) -> str:
    """
    Concatenates ``count`` random words as a hyphenated string.

    Wordlist is located in pyrolab/data/wordlist.txt.

    Parameters
    ----------
    count : int, optional
        How many words to use in the hyphenated string.

    Returns
    -------
    str
        A hyphenated string of ``count`` random words.
    """
    from pathlib import Path

    try:
        path = pkg_resources.files(pyrolab) / "data/wordlist.txt"
    except AttributeError:
        path = Path(pkg_resources.resource_filename("pyrolab", "data/wordlist.txt"))
    with open(path, "r") as f:
        wordlist = f.read().splitlines()

    return "-".join([secrets.choice(wordlist) for _ in range(count)])


def pid_is_running(pid: int) -> bool:
    """
    Return True if a process with the given PID currently exists.

    PIDs are reused, so True only means *some* process has this PID; callers
    that need certainty should also check that it answers as expected.

    Parameters
    ----------
    pid : int
        The process ID to check.

    Returns
    -------
    bool
        Whether the process exists.
    """
    if pid <= 0:
        return False
    if sys.platform == "win32":
        # os.kill() on Windows terminates the process instead of probing it.
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        # Declare types so 64-bit HANDLEs aren't truncated to a C int.
        kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.GetExitCodeProcess.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_ulong),
        ]
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            # Access denied means it exists but belongs to someone else.
            ERROR_ACCESS_DENIED = 5
            return ctypes.get_last_error() == ERROR_ACCESS_DENIED
        try:
            exit_code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return True
            return exit_code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, owned by another user
    return True


def atomic_write_text(path, text: str) -> None:
    """
    Write ``text`` to ``path`` so readers see the old contents or the new, never
    a partial file.

    The text goes to a temporary file in the same directory, which is flushed
    to disk and then replaces ``path`` in one step (``os.replace`` is atomic on
    POSIX and Windows). If anything fails, ``path`` is left untouched.

    Parameters
    ----------
    path : str or Path
        The file to write.
    text : str
        The new contents.
    """
    from pathlib import Path

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        with open(tmp, "w") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
