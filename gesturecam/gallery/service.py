"""Gallery operations over stored captures.

The service combines the :class:`~gesturecam.storage.database.CaptureDatabase`
(metadata) with filesystem operations (open in the OS viewer, delete the file,
export a copy). Deleting removes both the row and the underlying file.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

from ..errors import StorageError
from ..logging_setup import get_logger
from ..storage.database import CaptureDatabase
from ..storage.models import CaptureRecord

logger = get_logger(__name__)


class GalleryService:
    """High-level gallery actions backed by the capture database."""

    def __init__(self, database: CaptureDatabase) -> None:
        self._db = database

    def list_captures(self, *, limit: int | None = None) -> list[CaptureRecord]:
        return self._db.list(limit=limit)

    def open_in_viewer(self, record: CaptureRecord) -> None:  # pragma: no cover - OS dependent
        """Open the capture with the platform's default application."""
        path = Path(record.path)
        if not path.exists():
            raise StorageError(f"file no longer exists: {path}")
        system = platform.system()
        try:
            if system == "Darwin":
                subprocess.run(["open", str(path)], check=False)  # noqa: S603, S607
            elif system == "Windows":
                os.startfile(str(path))  # type: ignore[attr-defined]  # noqa: S606
            else:
                subprocess.run(["xdg-open", str(path)], check=False)  # noqa: S603, S607
        except OSError as exc:
            raise StorageError(f"failed to open {path}: {exc}") from exc

    def delete(self, record: CaptureRecord) -> None:
        """Remove the file from disk and its row from the database."""
        if record.id is None:
            raise StorageError("cannot delete a record without an id")
        path = Path(record.path)
        try:
            if path.exists():
                path.unlink()
        except OSError as exc:
            raise StorageError(f"failed to delete file {path}: {exc}") from exc
        self._db.delete(record.id)
        logger.info("Deleted capture %s", record.filename)

    def export(self, record: CaptureRecord, destination: Path) -> Path:
        """Copy a capture to ``destination`` (file or directory)."""
        source = Path(record.path)
        if not source.exists():
            raise StorageError(f"file no longer exists: {source}")
        target = destination / record.filename if destination.is_dir() else destination
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        except OSError as exc:
            raise StorageError(f"failed to export to {target}: {exc}") from exc
        logger.info("Exported %s to %s", record.filename, target)
        return target
