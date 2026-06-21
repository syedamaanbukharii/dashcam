"""Centralised logging configuration.

The whole application logs through the standard :mod:`logging` module - there
are no ``print`` statements anywhere in the codebase. Logs are written both to
the console and to a size-rotated file under :func:`gesturecam.paths.logs_dir`.

Call :func:`configure_logging` exactly once during application start-up.
Library modules obtain their logger with :func:`get_logger`.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import paths

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_MAX_BYTES = 2 * 1024 * 1024  # 2 MiB per file
_BACKUP_COUNT = 5

_configured = False


def configure_logging(level: str = "INFO", *, log_dir: Path | None = None) -> None:
    """Configure root logging with console and rotating-file handlers.

    Safe to call more than once; subsequent calls only adjust the level.
    """
    global _configured

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(numeric_level)

    if _configured:
        for handler in root.handlers:
            handler.setLevel(numeric_level)
        return

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(numeric_level)
    root.addHandler(console)

    directory = paths.ensure_dir(log_dir or paths.logs_dir())
    file_handler = RotatingFileHandler(
        directory / "gesturecam.log",
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(numeric_level)
    root.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger."""
    return logging.getLogger(name)
