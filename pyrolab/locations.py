# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Locations
=========

Where PyroLab keeps its files.

Each user gets their own configuration, logs, and runtime state, in the
platform's usual places (via ``platformdirs``)::

                Linux                     Windows                   macOS
    config      ~/.config/pyrolab         %LOCALAPPDATA%\\pyrolab     ~/Library/Application Support/pyrolab
    state       ~/.local/state/pyrolab    %LOCALAPPDATA%\\pyrolab     ~/Library/Application Support/pyrolab
    data        ~/.local/share/pyrolab    %LOCALAPPDATA%\\pyrolab     ~/Library/Application Support/pyrolab
    logs        ~/.local/state/pyrolab/log  %LOCALAPPDATA%\\pyrolab\\Logs  ~/Library/Logs/pyrolab
    cache       ~/.cache/pyrolab          %LOCALAPPDATA%\\pyrolab\\Cache ~/Library/Caches/pyrolab

Setting ``PYROLAB_DATA_DIR`` puts everything in that one directory instead
(logs in its ``logs`` subdirectory), e.g. for a shared service account.

Nothing here creates directories; files are created where they are written.
Versions before 0.5 kept everything inside the installed package, in
``pyrolab/data/local``; :py:func:`migrate_legacy_files` copies what is worth
keeping from there.
"""

import os
import shutil
from pathlib import Path
from typing import List, Mapping, NamedTuple

import platformdirs

APP_NAME = "pyrolab"
DATA_DIR_ENV_VAR = "PYROLAB_DATA_DIR"

# Where versions before 0.5 kept their files, inside the installed package.
LEGACY_DATA_DIR = Path(__file__).resolve().parent / "data" / "local"


class Locations(NamedTuple):
    config_dir: Path
    state_dir: Path
    data_dir: Path
    log_dir: Path
    cache_dir: Path


def locations(environ: Mapping[str, str] = os.environ) -> Locations:
    """
    Work out PyroLab's directories for the current user.

    Parameters
    ----------
    environ : Mapping[str, str], optional
        The environment to read ``PYROLAB_DATA_DIR`` from (default
        ``os.environ``).

    Returns
    -------
    Locations
        The config, state, data, log, and cache directories.
    """
    root = environ.get(DATA_DIR_ENV_VAR)
    if root:
        root = Path(root).expanduser()
        return Locations(root, root, root, root / "logs", root)
    dirs = platformdirs.PlatformDirs(APP_NAME, appauthor=False)
    return Locations(
        config_dir=Path(dirs.user_config_dir),
        state_dir=Path(dirs.user_state_dir),
        data_dir=Path(dirs.user_data_dir),
        log_dir=Path(dirs.user_log_dir),
        cache_dir=Path(dirs.user_cache_dir),
    )


def migrate_legacy_files(
    legacy_dir: Path, user_config_file: Path, nameserver_storage: Path, marker: Path
) -> List[str]:
    """
    Copy the configuration and nameserver databases from a pre-0.5 install.

    Runs once: afterwards ``marker`` records that it did, so a configuration
    the user later resets isn't brought back. Nothing that already exists at
    the new location is overwritten, and the old files are left in place.
    Logs, lockfiles, and runtime state aren't copied.

    Parameters
    ----------
    legacy_dir : Path
        The old ``pyrolab/data/local`` directory.
    user_config_file : Path
        Where the user configuration lives now.
    nameserver_storage : Path
        Where nameserver databases live now.
    marker : Path
        A file recording that migration has run.

    Returns
    -------
    List[str]
        A description of each file copied (empty if nothing was).
    """
    if marker.exists() or not legacy_dir.is_dir():
        return []

    copied = []

    def copy(src: Path, dst: Path) -> None:
        if src.is_file() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(f"{src} -> {dst}")

    copy(legacy_dir / "user_configuration.yaml", user_config_file)
    legacy_storage = legacy_dir / "nameserver"
    if legacy_storage.is_dir():
        for src in sorted(legacy_storage.iterdir()):
            copy(src, nameserver_storage / src.name)

    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        f"Copied from {legacy_dir}:\n" + "".join(f"{c}\n" for c in copied)
    )
    return copied
