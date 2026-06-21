"""Cross-platform application paths.

Resolves OS-appropriate directories for configuration, data, logs, models and
captures without hardcoding any absolute path. Honours the XDG Base Directory
specification on Linux, ``%APPDATA%``/``%LOCALAPPDATA%`` on Windows and the
``~/Library`` convention on macOS.

Every path-producing function returns a :class:`pathlib.Path`; nothing here
creates directories as a side effect except :func:`ensure_dir`, which callers
invoke explicitly.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "GestureCamPro"


def _home() -> Path:
    return Path.home()


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _is_macos() -> bool:
    return sys.platform == "darwin"


def config_dir() -> Path:
    """Directory for user configuration files."""
    if _is_windows():
        base = os.environ.get("APPDATA")
        root = Path(base) if base else _home() / "AppData" / "Roaming"
    elif _is_macos():
        root = _home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_CONFIG_HOME")
        root = Path(base) if base else _home() / ".config"
    return root / APP_DIR_NAME


def data_dir() -> Path:
    """Directory for persistent application data (database, models)."""
    if _is_windows():
        base = os.environ.get("LOCALAPPDATA")
        root = Path(base) if base else _home() / "AppData" / "Local"
    elif _is_macos():
        root = _home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME")
        root = Path(base) if base else _home() / ".local" / "share"
    return root / APP_DIR_NAME


def logs_dir() -> Path:
    """Directory for rotating log files."""
    return data_dir() / "logs"


def models_dir() -> Path:
    """Directory where downloaded ML model files are cached."""
    return data_dir() / "models"


def default_captures_dir() -> Path:
    """Default destination for captured photos and videos."""
    pictures = _home() / "Pictures"
    base = pictures if pictures.exists() else data_dir()
    return base / APP_DIR_NAME


def config_file() -> Path:
    """Path to the user configuration JSON file."""
    return config_dir() / "config.json"


def calibration_file() -> Path:
    """Path to the stored calibration profile."""
    return config_dir() / "calibration.json"


def database_file() -> Path:
    """Path to the SQLite database used by the gallery."""
    return data_dir() / "gesturecam.db"


def ensure_dir(path: Path) -> Path:
    """Create *path* (and parents) if missing and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path
