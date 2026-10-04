# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Server Resources
----------------

The scripts used for putting up and taking down Daemons and Workers from the
multiprocessing module. Since child processes need to be able to import the
script containing the target function, the target functions are contained
within this module where no new processes are ever spawned. The prevents
the recursive creation of new processes as the module is imported.

Server Resource Manager
-----------------------

The server resource manager handles the putting up and taking down of Daemons
for various instruments. To increase computer speed and processing
capabilities in cases where multiple instruments are hosted from the same
computer, each instrument is created in its own Daemon using the
Python ``multiprocessing`` module.

Lifecycle policy
----------------

* **Stopping** sends the stop message, waits :py:data:`STOP_GRACE` seconds for
  a clean exit, then terminates, waits :py:data:`TERMINATE_GRACE` seconds,
  then kills. An entity is forgotten only once its process is confirmed dead.
  A daemon that had to be killed can't deregister itself, so its nameserver
  entries are removed on its behalf.
* **Restarting**: a process that dies is restarted after an exponential
  backoff (:py:data:`RESTART_BACKOFF`). After
  :py:data:`MAX_CONSECUTIVE_FAILURES` crashes in a row it is marked failed and
  left alone until it is started again by hand (or by a reload). A process
  that stayed up for :py:data:`STABLE_UPTIME` seconds before dying starts a
  fresh count.
* **Registration** with nameservers never takes a daemon down: failures are
  logged and retried every :py:data:`REGISTRATION_RETRY` seconds, and every
  nameserver call times out after :py:data:`NAMESERVER_TIMEOUT` seconds.
"""

from __future__ import annotations

import functools
import logging
import math
import multiprocessing
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from multiprocessing import current_process
from multiprocessing.queues import Queue
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Tuple

from Pyro5.client import Proxy
from Pyro5.core import NAMESERVER_NAME

from pyrolab import RUNTIME_CONFIG
from pyrolab.configure import GlobalConfiguration, PyroLabConfiguration
from pyrolab.nameserver import start_ns_loop
from pyrolab.utils import get_ip

if TYPE_CHECKING:
    from Pyro5.core import URI

    from pyrolab.configure import (
        DaemonConfiguration,
        NameServerConfiguration,
        ServiceConfiguration,
    )
    from pyrolab.server import Daemon


log = logging.getLogger(__name__)

# Lifecycle timing, in seconds (see the module docstring).
STOP_GRACE = 10.0
TERMINATE_GRACE = 5.0
RESTART_BACKOFF = (5, 15, 60, 300)  # the last delay repeats
MAX_CONSECUTIVE_FAILURES = 5
STABLE_UPTIME = 600.0
CHECKUP_INTERVAL = 1.0
READY_TIMEOUT = 30.0
NAMESERVER_TIMEOUT = 5.0
REGISTRATION_RETRY = 30.0

NAMESERVER = "nameserver"
DAEMON = "daemon"


def describe_exception(exc: BaseException) -> str:
    """A one-line description of an exception, for ``ps`` and the CLI."""
    text = str(exc).strip().splitlines()
    detail = text[0] if text else ""
    line = f"{type(exc).__name__}: {detail}" if detail else type(exc).__name__
    return line if len(line) <= 200 else line[:197] + "..."


###############################################################################
# Nameserver registration
###############################################################################


@contextmanager
def nameserver_proxy(nscfg: NameServerConfiguration) -> Iterator[Proxy]:
    """
    A proxy to a configured nameserver, with a timeout, always released.

    Pyro's default is no timeout at all, so a nameserver host that silently
    drops packets would block the caller for minutes.
    """
    host = get_ip() if nscfg.host == "public" else nscfg.host
    proxy = Proxy(f"PYRO:{NAMESERVER_NAME}@{host}:{nscfg.ns_port}")
    proxy._pyroTimeout = NAMESERVER_TIMEOUT
    try:
        yield proxy
    finally:
        proxy._pyroRelease()


def remove_registrations(
    nameservers: Dict[str, NameServerConfiguration],
    names_by_nameserver: Dict[str, List[str]],
) -> None:
    """
    Best-effort removal of names from nameservers; failures are only logged.

    Parameters
    ----------
    nameservers : Dict[str, NameServerConfiguration]
        Configurations of the nameservers, by name.
    names_by_nameserver : Dict[str, List[str]]
        The registered names to remove from each nameserver.
    """
    for ns_name, names in names_by_nameserver.items():
        if not names or ns_name not in nameservers:
            continue
        try:
            with nameserver_proxy(nameservers[ns_name]) as ns:
                for name in names:
                    ns.remove(name)
        except Exception as e:
            log.warning(
                "Could not remove %s from nameserver '%s': %s",
                ", ".join(names),
                ns_name,
                describe_exception(e),
            )


def expected_registrations(
    name: str,
    daemonconfig: DaemonConfiguration,
    serviceconfigs: Dict[str, ServiceConfiguration],
) -> Dict[str, List[str]]:
    """The names a daemon registers, grouped by nameserver."""
    by_ns: Dict[str, List[str]] = {}
    for sname, svc in serviceconfigs.items():
        for ns in svc.nameservers:
            by_ns.setdefault(ns, []).append(sname)
    for ns in daemonconfig.nameservers:
        by_ns.setdefault(ns, []).append(name)
    return by_ns


class Registrations:
    """
    Tracks one daemon process's nameserver registrations.

    Registration is per nameserver and non-fatal: a nameserver that can't be
    reached leaves its entries pending (for :py:meth:`register_pending` to
    retry) without affecting the others. Each pass opens one short-lived
    proxy per nameserver and always releases it.

    Parameters
    ----------
    nameservers : Dict[str, NameServerConfiguration]
        Configurations of the nameservers that may be registered with.
    """

    def __init__(self, nameservers: Dict[str, NameServerConfiguration]) -> None:
        self.nameservers = nameservers
        self.pending: Dict[str, Dict[str, Tuple[URI, Optional[set]]]] = {}
        self.done: Dict[str, Dict[str, Tuple[URI, Optional[set]]]] = {}
        self._warned = set()
        self._lock = threading.Lock()

    def add(
        self, nameserver: str, name: str, uri: URI, metadata: Optional[set] = None
    ) -> None:
        """Queue ``name`` to be registered with ``nameserver``."""
        with self._lock:
            self.pending.setdefault(nameserver, {})[name] = (uri, metadata)

    def register_pending(self) -> bool:
        """
        Try every pending registration once.

        Returns
        -------
        bool
            True if nothing is left pending.
        """
        with self._lock:
            for ns_name in list(self.pending):
                entries = self.pending[ns_name]
                try:
                    with nameserver_proxy(self.nameservers[ns_name]) as ns:
                        for name in list(entries):
                            uri, metadata = entries[name]
                            ns.register(name, uri, metadata=metadata)
                            self.done.setdefault(ns_name, {})[name] = entries.pop(name)
                except Exception as e:
                    # Warn once per nameserver; retries would flood the log.
                    report = log.debug if ns_name in self._warned else log.warning
                    self._warned.add(ns_name)
                    report(
                        "Could not register %s with nameserver '%s' (retrying "
                        "every %gs): %s",
                        ", ".join(entries),
                        ns_name,
                        REGISTRATION_RETRY,
                        describe_exception(e),
                    )
                else:
                    if ns_name in self._warned:
                        log.info("Registered with nameserver '%s'", ns_name)
                        self._warned.discard(ns_name)
                if not entries:
                    del self.pending[ns_name]
            return not self.pending

    def remove_all(self) -> None:
        """Remove every registration this process made."""
        with self._lock:
            remove_registrations(
                self.nameservers,
                {ns: list(names) for ns, names in self.done.items()},
            )
            self.done.clear()


###############################################################################
# Child processes
###############################################################################


class NameServerRunner(multiprocessing.Process):
    """
    A process for running nameservers using Python's ``multiprocessing``.

    Advantages of using a child Process include the fact that if a server
    dies or hangs up, the entire program doesn't stall or need to be restarted,
    just the process that contained the server. Thus errors can be handled
    and servers autonomously restarted and managed.

    Parameters
    ----------
    name : str
        The name of the nameserver being run.
    nsconfig : NameServerConfiguration
        The configuration for the nameserver.
    msg_queue : multiprocessing.Queue
        A message queue. ResourceRunner listens for when ``None`` is placed
        in the queue, which is a sentinel value to shutdown the process.
    msg_polling : float, optional
        The time in seconds between polling the message queue.
    shared_state : dict, optional
        A dict shared with the manager (``multiprocessing.Manager().dict()``).
        The runner sets ``ready`` once it is serving, and ``error`` if it
        fails.
    """

    def __init__(
        self,
        *args,
        name: str = "",
        nsconfig: NameServerConfiguration = None,
        msg_queue: Queue = None,
        msg_polling: float = 1.0,
        shared_state: Optional[dict] = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        if not name:
            raise ValueError("NameServerRunner requires a name")
        if not nsconfig:
            raise ValueError("NameServerRunner requires a NameServerConfiguration")
        if not msg_queue:
            raise ValueError("NameServerRunner requires a message queue")

        self.name = name
        self.msg_queue: Queue = msg_queue
        self.msg_polling = msg_polling
        self.nsconfig = nsconfig
        self.state = shared_state if shared_state is not None else {}
        self.KILL_SIGNAL = False

    def process_message_queue(self) -> None:
        """
        A message handler.

        if the sentinel value ``None`` is placed in the message queue, sets
        a flag signifying a shutdown signal has been received.
        """
        self._timer = threading.Timer(self.msg_polling, self.process_message_queue)
        self._timer.daemon = True
        self._timer.start()

        if not self.msg_queue.empty():
            msg = self.msg_queue.get()
            log.debug(f"Message received: '{msg}'")
            if msg is None:
                log.info("KILL message received for nameserver '%s'", self.name)
                self.KILL_SIGNAL = True

    def stay_alive(self) -> bool:
        """
        A callback listener; if the sentinel value ``None`` is placed in the
        message queue, returns True signifying a shutdown signal has been
        received.

        This function is called by the Daemon's ``requestLoop()``.

        Returns
        -------
        bool
            True if shutdown signal received, False otherwise.
        """
        return not self.KILL_SIGNAL

    def run(self) -> None:
        """
        Creates and runs the child process.

        Any error is reported to the manager through ``shared_state`` before
        the process exits.
        """
        log.info("Starting nameserver '%s'", self.name)
        try:
            self.nsconfig.update_pyro_config()
            self.process_message_queue()
            start_ns_loop(
                self.nsconfig,
                loop_condition=self.stay_alive,
                on_ready=lambda: self.state.update(ready=True),
            )
        except BaseException as e:
            self.state["error"] = describe_exception(e)
            log.exception("Nameserver '%s' failed", self.name)
            raise
        finally:
            if hasattr(self, "_timer"):
                self._timer.cancel()


class DaemonRunner(multiprocessing.Process):
    """
    A process for running server daemons using Python's ``multiprocessing``.

    Advantages of using a ResourceRunner include the fact that if a server
    dies or hangs up, the entire program doesn't stall or need to be restarted,
    just the process that contained the server. Thus errors can be handled
    and servers autonomously restarted and managed.

    Other advantages should include speed; splitting servers across processors
    means that resource-heavy instruments won't bog down adjacent instruments.

    Parameters
    ----------
    name : str
        The name of the daemon being run.
    daemonconfig : DaemonConfiguration
        The configuration for the daemon.
    serviceconfigs : Dict[str, ServiceConfiguration]
        The configuration for the services belonging to the given daemon.
    msg_queue : multiprocessing.Queue
        A message queue. ResourceRunner listens for when "None" is placed
        in the queue, which is a sentinel value to shutdown the process.
    shared_uris : dict
        A dict shared with the manager, filled with each hosted object's URI.
    msg_polling : float, optional
        The time in seconds between polling the message queue.
    shared_state : dict, optional
        A dict shared with the manager. The runner sets ``ready`` once it is
        serving, and ``error`` if it fails.
    """

    def __init__(
        self,
        *args,
        name: str,
        daemonconfig: DaemonConfiguration,
        serviceconfigs: Dict[str, ServiceConfiguration],
        msg_queue: Queue,
        shared_uris: dict[str, URI],
        msg_polling: float = 1.0,
        shared_state: Optional[dict] = None,
        **kwargs,
    ) -> None:
        log.debug("Building DaemonRunner")
        super().__init__(*args, **kwargs)
        self.name = name
        self.msg_queue: Queue = msg_queue
        self.uris = shared_uris
        self.msg_polling = msg_polling
        self.daemonconfig = daemonconfig
        self.serviceconfigs = serviceconfigs
        self.state = shared_state if shared_state is not None else {}
        self.KILL_SIGNAL = False

    def setup_daemon(self) -> Tuple[Daemon, Dict[str, URI]]:
        """
        Locates and loads the Daemon class, adds Pyro's ``behavior``, and
        registers the hosted object with the Daemon.

        Returns
        -------
        daemon, uri
            The instantiated Daemon object and the URI for the hosted object,
            to be registered with the nameserver.
        """
        daemon = self.daemonconfig._get_daemon()
        daemon = daemon()

        uris = {}
        for sname, sconfig in self.serviceconfigs.items():
            log.info(f"Registering service '{sname}'")
            service = sconfig._get_service()

            log.debug("Getting service uri")
            uri = daemon.register(service)
            uris[sname] = uri
            log.info("URI for '%s' = %s", sname, uri)

        if self.daemonconfig.nameservers:
            log.debug("Self-registering daemon")
            uri = daemon.register(daemon)
            uris[self.name] = uri

        self.uris.clear()
        self.uris.update(uris)
        return daemon, uris

    def process_message_queue(self) -> None:
        """
        A message handler.

        if the sentinel value ``None`` is placed in the message queue, sets
        a flag signifying a shutdown signal has been received.
        """
        self._timer = threading.Timer(self.msg_polling, self.process_message_queue)
        self._timer.daemon = True
        self._timer.start()

        if not self.msg_queue.empty():
            msg = self.msg_queue.get()
            if msg is None:
                log.info("KILL message received for daemon '%s'", self.name)
                self.KILL_SIGNAL = True

    def stay_alive(self) -> bool:
        """
        A callback listener; if the sentinel value ``None`` is placed in the
        message queue, returns True signifying a shutdown signal has been
        received.

        This function is called by the Daemon's ``requestLoop()``.

        Returns
        -------
        bool
            True if shutdown signal received, False otherwise.
        """
        return not self.KILL_SIGNAL

    def plan_registrations(self, uris: Dict[str, URI]) -> Registrations:
        """Queue every nameserver registration this daemon should make."""
        config = PyroLabConfiguration.from_file(RUNTIME_CONFIG)
        registrations = Registrations(config.nameservers)
        for sname, svc in self.serviceconfigs.items():
            metadata = {svc.description} if svc.description else None
            for ns in svc.nameservers:
                registrations.add(ns, sname, uris[sname], metadata)
        if self.daemonconfig.nameservers:
            services = ", ".join(str(sname) for sname in self.serviceconfigs)
            for ns in self.daemonconfig.nameservers:
                registrations.add(
                    ns, self.name, uris[self.name], {f"Daemon for {services}"}
                )
        return registrations

    def run(self) -> None:
        """
        Creates and runs the child process.

        Services are served as soon as they are set up; registering them with
        nameservers happens in the background and is retried until it
        succeeds, so an unreachable nameserver never takes the daemon down.
        When the kill signal is received, removes its registrations and exits.
        Any error is reported to the manager through ``shared_state``.
        """
        log.info("Starting daemon '%s'", self.name)
        stop_registering = threading.Event()
        registrar = None
        try:
            self.daemonconfig.update_pyro_config()
            daemon, uris = self.setup_daemon()
            registrations = self.plan_registrations(uris)

            def keep_registering():
                while not registrations.register_pending():
                    if stop_registering.wait(REGISTRATION_RETRY):
                        return

            registrar = threading.Thread(
                target=keep_registering, name="registration", daemon=True
            )
            registrar.start()

            self.process_message_queue()
            self.state["ready"] = True
            log.debug("entering request loop for '%s'", self.name)
            daemon.requestLoop(loopCondition=self.stay_alive)
            log.info("Daemon '%s' is shutting down.", self.name)

            stop_registering.set()
            registrar.join(timeout=NAMESERVER_TIMEOUT + 1)
            registrations.remove_all()
            daemon.close()
        except BaseException as e:
            self.state["error"] = describe_exception(e)
            log.exception("Daemon '%s' failed", self.name)
            raise
        finally:
            stop_registering.set()
            if hasattr(self, "_timer"):
                self._timer.cancel()


###############################################################################
# Process bookkeeping
###############################################################################

RUNNING = "running"
STOPPING = "stopping"
RESTARTING = "restarting"
FAILED = "failed"


class ProcessGroup:
    """
    One managed child process and its restart bookkeeping.

    Parameters
    ----------
    process : multiprocessing.Process
        The runner.
    msg_queue : Queue
        Its message queue (``None`` asks it to stop).
    created : datetime
        When it was started, for display.
    shared_uris : dict, optional
        URIs the runner publishes (daemons only).
    shared_state : dict, optional
        ``ready``/``error`` flags the runner publishes.
    """

    def __init__(
        self,
        process,
        msg_queue,
        created: datetime,
        shared_uris: Optional[dict] = None,
        shared_state: Optional[dict] = None,
    ) -> None:
        self.process = process
        self.msg_queue = msg_queue
        self.created = created
        self.shared_uris = shared_uris if shared_uris is not None else {}
        self.shared_state = shared_state if shared_state is not None else {}
        self.started = time.monotonic()  # the manager overrides with its clock
        self.status = RUNNING
        self.failures = 0  # consecutive crashes
        self.last_error = ""
        self.retry_at: Optional[float] = None


class NameServerProcessGroup(ProcessGroup):
    pass


class DaemonProcessGroup(ProcessGroup):
    pass


def _synchronized(method):
    """Run a ProcessManager method while holding the manager's lock."""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper


class ProcessManager:
    """
    A manager class for running a set of PyroLab processes.

    ProcessManager is a singleton. Access the global object by calling
    :py:func:`instance`. Only the main process can access the ProcessManager.
    See the module docstring for the stop, restart, and registration policy.
    """

    _instance = None
    # Pyro request threads, the checkup timer, and the background autolaunch
    # all use the singleton concurrently; anything that reads or changes the
    # process tables holds this lock. Long waits (for a process to stop or to
    # become ready, or for a nameserver) happen outside it, so `ps` stays
    # responsive. Reentrant, since locked methods call each other.
    _lock = threading.RLock()
    nameservers: Dict[str, NameServerProcessGroup]
    daemons: Dict[str, DaemonProcessGroup]
    GLOBAL_CONFIG: GlobalConfiguration
    manager: multiprocessing.Manager
    _timer: threading.Timer

    def __init__(self) -> None:
        raise RuntimeError(
            "Cannot directly instantiate singleton, call ``instance()`` instead."
        )

    @classmethod
    def instance(cls) -> "ProcessManager":
        """
        Get the singleton instance of the ProcessManager.

        Only the main process can access the ProcessManager.

        Returns
        -------
        ProcessManager
            The singleton instance of the ProcessManager.

        Raises
        ------
        RuntimeError
            If the requesting process is not the main process.
        """
        log.debug("ProcessManager instance requested")
        if current_process().name != "MainProcess":
            log.critical("ProcessManager instance requested from non-main process")
            raise Exception(
                "ProcessManager should only be accessed by the main process."
            )
        if cls._instance is None:
            log.debug("ProcessManager instance did not exist, created")
            inst = cls.__new__(cls)
            inst.nameservers = {}
            inst.daemons = {}
            inst.GLOBAL_CONFIG = GlobalConfiguration.instance()
            inst.manager = multiprocessing.Manager()
            cls._instance = inst
            # Last: checkup() relaunches processes, which needs everything above.
            inst.start_checkup_timer()
        return cls._instance

    # Seams for tests -------------------------------------------------------

    def _clock(self) -> float:
        return time.monotonic()

    def _shared_dict(self) -> dict:
        return self.manager.dict()

    def _message_queue(self):
        return multiprocessing.Queue()

    def _create_runner(self, kind: str, name: str, msg_queue, shared_state, uris):
        if kind == NAMESERVER:
            return NameServerRunner(
                name=name,
                nsconfig=self.GLOBAL_CONFIG.get_nameserver_config(name),
                msg_queue=msg_queue,
                shared_state=shared_state,
                daemon=True,
            )
        return DaemonRunner(
            name=name,
            daemonconfig=self.GLOBAL_CONFIG.get_daemon_config(name),
            serviceconfigs=self.GLOBAL_CONFIG.get_service_configs_for_daemon(name),
            msg_queue=msg_queue,
            shared_uris=uris,
            shared_state=shared_state,
            daemon=True,
        )

    # Internals --------------------------------------------------------------

    def _table(self, kind: str) -> Dict[str, ProcessGroup]:
        return self.nameservers if kind == NAMESERVER else self.daemons

    def _configured(self, kind: str) -> dict:
        config = self.GLOBAL_CONFIG.config
        return config.nameservers if kind == NAMESERVER else config.daemons

    def _spawn(self, kind: str, name: str) -> ProcessGroup:
        """Start a runner and return its (not yet tabled) group."""
        msg_queue = self._message_queue()
        shared_state = self._shared_dict()
        uris = self._shared_dict() if kind == DAEMON else None
        runner = self._create_runner(kind, name, msg_queue, shared_state, uris)
        cls = NameServerProcessGroup if kind == NAMESERVER else DaemonProcessGroup
        group = cls(runner, msg_queue, datetime.now(), uris, shared_state)
        group.started = self._clock()
        runner.start()
        return group

    def _death_reason(self, group: ProcessGroup) -> str:
        error = group.shared_state.get("error")
        return error or f"exited with code {group.process.exitcode}"

    def _record_death(self, kind: str, name: str, group: ProcessGroup) -> None:
        """Note a crash and schedule a restart, or give up. Caller holds lock."""
        now = self._clock()
        group.process.join(timeout=0)  # reap
        if now - group.started >= STABLE_UPTIME:
            group.failures = 0  # it had been healthy; this is a fresh problem
        group.failures += 1
        group.last_error = self._death_reason(group)
        if group.failures >= MAX_CONSECUTIVE_FAILURES:
            group.status = FAILED
            log.error(
                "%s '%s' crashed %d times in a row; not restarting it until it "
                "is started again. Last error: %s",
                kind.capitalize(),
                name,
                group.failures,
                group.last_error,
            )
        else:
            delay = RESTART_BACKOFF[min(group.failures, len(RESTART_BACKOFF)) - 1]
            group.status = RESTARTING
            group.retry_at = now + delay
            log.warning(
                "%s '%s' died (%s); restarting in %gs (crash %d of %d).",
                kind.capitalize(),
                name,
                group.last_error,
                delay,
                group.failures,
                MAX_CONSECUTIVE_FAILURES,
            )

    def _registrations_of(self, kind: str, group: ProcessGroup) -> Dict[str, List[str]]:
        """What a (daemon) group registers with nameservers, per its config."""
        process = group.process
        if kind != DAEMON or not hasattr(process, "daemonconfig"):
            return {}
        return expected_registrations(
            process.name, process.daemonconfig, process.serviceconfigs
        )

    def _cleanup_registrations(self, entries) -> None:
        """Remove registrations for dead daemons. Call without the lock."""
        if not entries:
            return
        nameservers = self.GLOBAL_CONFIG.config.nameservers
        for kind, group in entries:
            names = self._registrations_of(kind, group)
            if names:
                remove_registrations(nameservers, names)

    def _status_text(self, group: ProcessGroup) -> str:
        if group.status == FAILED:
            return f"Failed ({group.failures} crashes)"
        if group.status == RESTARTING:
            wait = max(0, math.ceil(group.retry_at - self._clock()))
            return (
                f"Restarting in {wait}s ({group.failures}/{MAX_CONSECUTIVE_FAILURES})"
            )
        if group.status == STOPPING:
            return "Stopping"
        if not group.process.is_alive():
            return "Died"
        if not group.shared_state.get("ready"):
            return "Starting"
        return running_time_human_readable(group.created)

    def _info(self, group: Optional[ProcessGroup]) -> Dict[str, str]:
        if group is None:
            return {"created": "", "status": "Stopped", "error": ""}
        if group.status == RUNNING and not group.process.is_alive():
            error = self._death_reason(group)  # crashed; checkup hasn't run yet
        elif group.status in (RESTARTING, FAILED):
            error = group.last_error
        else:
            error = ""
        return {
            "created": group.created.strftime("%Y-%m-%d %H:%M:%S"),
            "status": self._status_text(group),
            "error": error,
        }

    # Timer -------------------------------------------------------------------

    def start_checkup_timer(self, duration: float = CHECKUP_INTERVAL) -> None:
        """
        Starts a timer to check up on the processes after ``duration`` seconds.
        """
        self._timer = threading.Timer(duration, self.checkup)
        self._timer.daemon = True
        self._timer.start()

    def stop_checkup_timer(self) -> None:
        """
        Stops the checkup timer.
        """
        log.debug("Stopping checkup timer")
        if hasattr(self, "_timer"):
            self._timer.cancel()

    # Starting ----------------------------------------------------------------

    def _launch(self, kind: str, name: str, wait: bool, timeout: float) -> dict:
        with self._lock:
            if name not in self._configured(kind):
                return {"status": "unknown", "error": ""}
            table = self._table(kind)
            current = table.get(name)
            if current is not None and (
                current.status == STOPPING or current.process.is_alive()
            ):
                return {"status": "already running", "error": ""}
            log.info("Launching %s '%s'", kind, name)
            # A manual start (or reload) gives a crashed or failed entity a
            # fresh failure count.
            try:
                group = self._spawn(kind, name)
            except Exception as e:
                log.exception("Launching %s '%s' failed", kind, name)
                return {"status": "failed", "error": describe_exception(e)}
            table[name] = group
        if not wait:
            return {"status": "started", "error": ""}
        return self._await_ready(group, timeout)

    def _await_ready(self, group: ProcessGroup, timeout: float) -> dict:
        """Wait (without the lock) for a runner to report ready or die."""
        deadline = time.monotonic() + timeout
        while True:
            if group.shared_state.get("ready"):
                return {"status": "running", "error": ""}
            if not group.process.is_alive():
                return {"status": "failed", "error": self._death_reason(group)}
            if time.monotonic() >= deadline:
                return {"status": "timeout", "error": ""}
            time.sleep(0.05)

    def launch_nameserver(
        self, nameserver: str, wait: bool = False, timeout: float = READY_TIMEOUT
    ) -> dict:
        """
        Launch a nameserver.

        Parameters
        ----------
        nameserver : str
            The name of the nameserver, as configured.
        wait : bool, optional
            Wait until it is serving (or has died, or ``timeout`` passed).
        timeout : float, optional
            How long to wait, in seconds.

        Returns
        -------
        dict
            ``status`` is one of "started" (not waited for), "running",
            "failed", "timeout", "already running", or "unknown" (not in the
            configuration); ``error`` describes a failure.
        """
        return self._launch(NAMESERVER, nameserver, wait, timeout)

    def launch_daemon(
        self, daemon: str, wait: bool = False, timeout: float = READY_TIMEOUT
    ) -> dict:
        """
        Launch a daemon and all its associated services.

        Parameters and return value are as for :py:meth:`launch_nameserver`.
        """
        return self._launch(DAEMON, daemon, wait, timeout)

    # Status ------------------------------------------------------------------

    @_synchronized
    def get_nameserver_process_info(self, nameserver: str) -> Dict[str, str]:
        """
        Gets info on a nameserver process.

        Parameters
        ----------
        nameserver : str
            The name of the nameserver.

        Returns
        -------
        Dict[str, str]
            Keys are ``created``, ``status``, ``uri``, and ``error`` (the last
            failure, while the nameserver is crashed or restarting).
        """
        group = self.nameservers.get(nameserver)
        info = self._info(group)
        uri = ""
        if group is not None and hasattr(group.process, "nsconfig"):
            uri = f"{group.process.nsconfig.host}:{group.process.nsconfig.ns_port}"
        return {**info, "uri": uri}

    @_synchronized
    def get_daemon_process_info(self, daemon: str) -> Dict[str, str]:
        """
        Gets info on a daemon process; keys as for
        :py:meth:`get_nameserver_process_info`.
        """
        group = self.daemons.get(daemon)
        info = self._info(group)
        uri = ""
        if group is not None and daemon in group.shared_uris:
            uri = str(group.shared_uris[daemon])
        return {**info, "uri": uri}

    @_synchronized
    def get_service_process_info(self, service: str) -> Dict[str, str]:
        """
        Return the process info for a service.
        """
        for daemon_name, daemon in self.daemons.items():
            for srvc_name in daemon.process.serviceconfigs:
                if srvc_name == service:
                    if service in daemon.shared_uris:
                        uri = str(daemon.shared_uris[service])
                    else:
                        uri = ""
                    return {
                        "daemon": daemon_name,
                        "uri": uri,
                    }
        return {
            "daemon": "",
            "uri": "",
        }

    # Health ------------------------------------------------------------------

    def checkup(self, continuous: bool = True) -> None:
        """
        Notice crashed processes and restart them per the backoff policy.
        """
        gave_up = []
        with self._lock:
            now = self._clock()
            for kind in (NAMESERVER, DAEMON):
                table = self._table(kind)
                for name, group in list(table.items()):
                    if group.status == RUNNING and not group.process.is_alive():
                        self._record_death(kind, name, group)
                        if group.status == FAILED:
                            gave_up.append((kind, group))
                    elif group.status == RESTARTING and now >= group.retry_at:
                        try:
                            replacement = self._spawn(kind, name)
                        except Exception as e:
                            log.exception("Restarting %s '%s' failed", kind, name)
                            group.shared_state = {"error": describe_exception(e)}
                            group.started = now
                            self._record_death(kind, name, group)
                            continue
                        replacement.failures = group.failures
                        replacement.last_error = group.last_error
                        table[name] = replacement
        # Registrations left behind by a process that won't come back would
        # point clients at a dead URI.
        self._cleanup_registrations(gave_up)
        if continuous:
            self.start_checkup_timer()

    # Stopping ----------------------------------------------------------------

    def _stop_many(self, entries: List[Tuple[str, str]]) -> Dict[Tuple[str, str], bool]:
        """
        Stop several entities at once: all are asked to stop, then waited for
        together, so the total wait is one grace period rather than one each.
        """
        results = {}
        stopping = []
        with self._lock:
            for kind, name in entries:
                group = self._table(kind).get(name)
                if group is None or group.status == STOPPING:
                    log.warning("Cannot stop %s '%s': not running", kind, name)
                    results[(kind, name)] = False
                elif not group.process.is_alive():
                    # Crashed, restarting, or failed: just forget it.
                    group.process.join(timeout=0)
                    del self._table(kind)[name]
                    results[(kind, name)] = True
                else:
                    log.info("Stopping %s '%s'", kind, name)
                    group.status = STOPPING
                    group.msg_queue.put(None)
                    stopping.append((kind, name, group))

        forced = []
        for limit, escalate in (
            (STOP_GRACE, "terminate"),
            (TERMINATE_GRACE, "kill"),
            (TERMINATE_GRACE, None),
        ):
            deadline = time.monotonic() + limit
            for kind, name, group in stopping:
                group.process.join(max(0.0, deadline - time.monotonic()))
            alive = [entry for entry in stopping if entry[2].process.is_alive()]
            if not alive or escalate is None:
                break
            for kind, name, group in alive:
                log.warning(
                    "%s '%s' did not exit; sending %s",
                    kind.capitalize(),
                    name,
                    escalate,
                )
                getattr(group.process, escalate)()
                if (kind, group) not in forced:
                    forced.append((kind, group))

        with self._lock:
            for kind, name, group in stopping:
                dead = not group.process.is_alive()
                results[(kind, name)] = dead
                if dead:
                    if self._table(kind).get(name) is group:
                        del self._table(kind)[name]
                else:
                    log.error("%s '%s' could not be killed", kind.capitalize(), name)
        # A killed daemon didn't get to deregister itself.
        self._cleanup_registrations(
            [(kind, group) for kind, group in forced if not group.process.is_alive()]
        )
        return results

    def shutdown_nameserver(self, nameserver: str) -> bool:
        """
        Stop a nameserver, escalating to terminate/kill if it doesn't exit.

        Returns
        -------
        bool
            True once the process is confirmed dead; False if no nameserver by
            that name is running, or it could not be killed.
        """
        return self._stop_many([(NAMESERVER, nameserver)])[(NAMESERVER, nameserver)]

    def shutdown_daemon(self, daemon: str) -> bool:
        """
        Stop a daemon and its services; see :py:meth:`shutdown_nameserver`.
        """
        return self._stop_many([(DAEMON, daemon)])[(DAEMON, daemon)]

    def reload(self) -> bool:
        """
        Restart every managed entity with the current configuration.

        Entities no longer in the configuration are stopped and not restarted.
        Crashed or failed ones are given a fresh start.

        Returns
        -------
        bool
            True only if everything stopped cleanly and every relaunched
            entity reported ready.
        """
        log.info("Reloading all running entities.")
        self.stop_checkup_timer()
        with self._lock:
            nameservers = list(self.nameservers)
            daemons = list(self.daemons)

        # Daemons first, so they can deregister while their nameservers are up.
        stopped = self._stop_many([(DAEMON, name) for name in daemons])
        stopped.update(self._stop_many([(NAMESERVER, name) for name in nameservers]))
        ok = all(stopped.values())

        # Nameservers first, so daemons can register with them.
        for kind, names in ((NAMESERVER, nameservers), (DAEMON, daemons)):
            launched = [
                (name, self._launch(kind, name, wait=False, timeout=READY_TIMEOUT))
                for name in names
                if name in self._configured(kind)
            ]
            for name, result in launched:
                if result["status"] != "started":
                    ok = False
                    continue
                with self._lock:
                    group = self._table(kind).get(name)
                if group is None or (
                    self._await_ready(group, READY_TIMEOUT)["status"] != "running"
                ):
                    log.error("%s '%s' did not come back after reload", kind, name)
                    ok = False

        self.start_checkup_timer()
        return ok

    def shutdown_all(self) -> None:
        """
        Shutdown all entities.
        """
        log.info("Shutting down all running entities.")

        self.stop_checkup_timer()

        with self._lock:
            daemons = list(self.daemons)
            nameservers = list(self.nameservers)
        self._stop_many([(DAEMON, name) for name in daemons])
        self._stop_many([(NAMESERVER, name) for name in nameservers])

        # The multiprocessing.Manager runs its own server process; without
        # this it can outlive the daemon.
        manager = getattr(self, "manager", None)
        if manager is not None:
            manager.shutdown()
            self.manager = None
        # Everything this instance owned is gone; let a later instance() call
        # build a fresh one rather than hand back this shut-down one.
        if ProcessManager._instance is self:
            ProcessManager._instance = None

        log.info("All running entities shut down.")


def running_time_human_readable(start: datetime, end: datetime = None) -> str:
    """
    Return the time elapsed between two times (or one and now), for ``ps``.

    Shows the two most significant units, e.g. "Up 6d 23h", "Up 4h 0m",
    "Up 45s".

    Parameters
    ----------
    start : datetime
        The start time.
    end : datetime, optional
        The end time. Defaults to now.

    Returns
    -------
    str
        The elapsed time, e.g. "Up 2d 5h".
    """
    if end is None:
        end = datetime.now()
    # Clamp at zero in case the clock moved backwards.
    remaining = max(0, int((end - start).total_seconds()))

    parts = []
    for suffix, size in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        value, remaining = divmod(remaining, size)
        if value or parts:
            parts.append(f"{value}{suffix}")
        if len(parts) == 2:
            break
    return "Up " + (" ".join(parts) or "0s")
