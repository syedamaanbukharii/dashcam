"""Tests for the SQLite capture database (in-memory)."""

from __future__ import annotations

import pytest

from gesturecam.storage.database import CaptureDatabase
from gesturecam.storage.models import CaptureRecord


def _record(filename: str, media_type: str = "photo", score: float = 0.5) -> CaptureRecord:
    return CaptureRecord(
        filename=filename,
        path=f"captures/{filename}",
        media_type=media_type,
        created_at="2026-01-01T00:00:00",
        score=score,
        width=1280,
        height=720,
        metadata={"gesture": "peace"},
    )


@pytest.fixture()
def db():
    database = CaptureDatabase(":memory:")
    yield database
    database.close()


def test_add_assigns_id(db) -> None:
    saved = db.add(_record("a.jpg"))
    assert saved.id is not None
    assert db.count() == 1


def test_get_round_trips_metadata(db) -> None:
    saved = db.add(_record("b.jpg"))
    fetched = db.get(saved.id)
    assert fetched is not None
    assert fetched.filename == "b.jpg"
    assert fetched.metadata == {"gesture": "peace"}


def test_list_is_newest_first(db) -> None:
    first = db.add(_record("first.jpg"))
    second = db.add(_record("second.jpg"))
    records = db.list()
    assert [r.id for r in records] == [second.id, first.id]


def test_list_filters_by_media_type(db) -> None:
    db.add(_record("photo.jpg", media_type="photo"))
    db.add(_record("clip.mp4", media_type="video"))
    videos = db.list(media_type="video")
    assert len(videos) == 1
    assert videos[0].media_type == "video"


def test_list_respects_limit(db) -> None:
    for i in range(5):
        db.add(_record(f"img_{i}.jpg"))
    assert len(db.list(limit=2)) == 2


def test_delete_removes_record(db) -> None:
    saved = db.add(_record("gone.jpg"))
    assert db.delete(saved.id) is True
    assert db.get(saved.id) is None
    assert db.delete(saved.id) is False  # already gone


def test_context_manager_closes() -> None:
    with CaptureDatabase(":memory:") as database:
        database.add(_record("ctx.jpg"))
        assert database.count() == 1
