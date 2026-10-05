.. _user_guide:


Files, Logs, and Environment Variables
======================================

Where PyroLab keeps its files
-----------------------------

Each user has their own PyroLab configuration, logs, and runtime state, kept in
the platform's usual places rather than inside the installed package (so
upgrading PyroLab never touches them):

.. list-table::
   :header-rows: 1

   * -
     - Linux
     - Windows
     - macOS
   * - Configuration
     - ``~/.config/pyrolab``
     - ``%LOCALAPPDATA%\pyrolab``
     - ``~/Library/Application Support/pyrolab``
   * - Logs
     - ``~/.local/state/pyrolab/log``
     - ``%LOCALAPPDATA%\pyrolab\Logs``
     - ``~/Library/Logs/pyrolab``
   * - Runtime state
     - ``~/.local/state/pyrolab``
     - ``%LOCALAPPDATA%\pyrolab``
     - ``~/Library/Application Support/pyrolab``
   * - Nameserver data
     - ``~/.local/share/pyrolab``
     - ``%LOCALAPPDATA%\pyrolab``
     - ``~/Library/Application Support/pyrolab``

``pyrolab --data`` prints the exact paths on your machine. Set
``PYROLAB_DATA_DIR`` (below) to keep everything in one directory instead.

Versions before 0.5 kept these files inside the installed package. The first
time you run a ``pyrolab`` command after upgrading, it copies your
configuration and nameserver databases to the new locations (once, without
overwriting anything, and leaving the originals in place).


Logs
----

The background daemon writes a single log file, ``pyrolab.log``, for itself and
every nameserver and daemon it runs. It rotates at 5 MB, keeping five older
files. Each line is one JSON record. Rather than reading it directly:

``pyrolab status``
   Whether the daemon is running, and the warnings and errors logged since it
   started.
``pyrolab logs show``
   The log since the daemon last started (``--level``, ``--all``, ``--lines``).
``pyrolab logs export FILE``
   The whole log as text (or ``--json``), to attach to a bug report.
``pyrolab logs clean``
   Delete the logs (stop the daemon first).

Output the daemon itself prints (such as a crash in a child process before it
could log) goes to ``pyrolabd_output.log`` beside the log.

When you use PyroLab as a library (in a client script), it writes no log
files and leaves your application's logging alone; its messages go wherever
your application sends the ``pyrolab`` loggers.


Environment variables
---------------------

``PYROLAB_DATA_DIR``
   Keep all of PyroLab's files in this directory (logs in its ``logs``
   subdirectory) instead of the per-user locations above.
``PYROLAB_LOGFILE``
   Where the daemon writes its log, instead of ``pyrolab.log`` in the log
   directory.
``PYROLAB_LOGLEVEL``
   The level to log at (``DEBUG``, ``INFO``, ``WARNING``, ...; default
   ``INFO``). For the daemon this sets what goes into the log; when set, other
   ``pyrolab`` commands also print their own log messages to the terminal.
``PYROLAB_HUSH_DEPRECATION``
   If set, the ``pyrolab`` command and daemon hide DeprecationWarnings.
``PYROLAB_NO_VERSION_CHECK``
   If set (to any value), the ``pyrolab`` command line tool never checks PyPI
   for a newer release. Otherwise it checks at most once a day, with a short
   timeout, and caches the result (including a failed check) so that machines
   on isolated networks don't wait on every command. Importing ``pyrolab`` as
   a library never checks.
