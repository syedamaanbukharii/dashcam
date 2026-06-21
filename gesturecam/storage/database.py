"""SQLite persistence for capture metadata.

The database is intentionally tiny: a single ``captures`` table. Access is
guarded by a lock and the connection is opened with ``check_same_thread=False``
so the engine, gallery and UI threads can share one :class:`CaptureDatabase`.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from ..errors import StorageError
from ..logging_setup import get_logger
from ..paths import ensure_dir
from .models import CaptureRecord

logger = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS captures (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filename    TEXT    NOT NULL,
    path        TEXT    NOT NULL,
    media_type  TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    score       REAL    NOT NULL DEFAULT 0,
    width       INTEGER NOT NULL DEFAULT 0,
    height      INTEGER NOT NULL DEFAULT 0,
    metadata    TEXT    NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_captures_created_at ON captures (created_at DESC);
"""


class CaptureDatabase:
    """A thread-safe wrapper around the captures SQLite table."""

    def __init__(self, db_path: Path | str) -> None:
        self._path = str(db_path)
        if self._path != ":memory:":
            ensure_dir(Path(self._path).parent)
        self._lock = threading.Lock()
        try:
            self._conn = sqlite3.connect(self._path, check_same_thread=False)
        except sqlite3.Error as exc:
            raise StorageError(f"failed to open database at {self._path}: {exc}") from exc
        self._conn.row_factory = sqlite3.Row
        self._initialise()

    def _initialise(self) -> None:
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # -- writes ------------------------------------------------------------
    def add(self, record: CaptureRecord) -> CaptureRecord:
        """Insert a record and return it with its assigned ``id``."""
        with self._lock:
            cursor = self._conn.execute(
                """
                INSERT INTO captures
                    (filename, path, media_type, created_at, score, width, height, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.filename,
                    record.path,
                    record.media_type,
                    record.created_at,
                    record.score,
                    record.width,
                    record.height,
                    record.metadata_json(),
                ),
            )
            self._conn.commit()
            record.id = int(cursor.lastrowid or 0)
        logger.debug("Stored capture %s (id=%s)", record.filename, record.id)
        return record

    def delete(self, record_id: int) -> bool:
        """Delete a record by id; returns ``True`` if a row was removed."""
        with self._lock:
            cursor = self._conn.execute("DELETE FROM captures WHERE id = ?", (record_id,))
            self._conn.commit()
            return cursor.rowcount > 0

    # -- reads -------------------------------------------------------------
    def get(self, record_id: int) -> CaptureRecord | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM captures WHERE id = ?", (record_id,)).fetchone()
        return self._row_to_record(row) if row else None

    def list(
        self, *, limit: int | None = None, media_type: str | None = None
    ) -> list[CaptureRecord]:
        """Return records newest-first, optionally filtered/limited."""
        query = "SELECT * FROM captures"
        params: list[object] = []
        if media_type is not None:
            query += " WHERE media_type = ?"
            params.append(media_type)
        query += " ORDER BY datetime(created_at) DESC, id DESC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(int(limit))
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    def count(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM captures").fetchone()
        return int(row["n"]) if row else 0

    # -- lifecycle ---------------------------------------------------------
    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self) -> CaptureDatabase:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> CaptureRecord:
        return CaptureRecord(
            id=int(row["id"]),
            filename=row["filename"],
            path=row["path"],
            media_type=row["media_type"],
            created_at=row["created_at"],
            score=float(row["score"]),
            width=int(row["width"]),
            height=int(row["height"]),
            metadata=CaptureRecord.parse_metadata(row["metadata"]),
        )
