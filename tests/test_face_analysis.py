"""Tests for face framing analysis."""

from __future__ import annotations

from gesturecam.face.analysis import PositioningParams, analyze_positioning, largest_face
from gesturecam.face.types import FaceBox, FaceIssue

_W = 1000
_H = 1000


def _centered_box(side: int) -> FaceBox:
    x = (_W - side) // 2
    y = (_H - side) // 2
    return FaceBox(x=x, y=y, width=side, height=side)


def test_centered_face_is_ready() -> None:
    result = analyze_positioning([_centered_box(300)], _W, _H)
    assert result.ready is True
    assert result.issues == []
    assert result.guidance == "Looking good!"


def test_no_face_reported() -> None:
    result = analyze_positioning([], _W, _H)
    assert result.ready is False
    assert FaceIssue.NO_FACE in result.issues


def test_face_too_far() -> None:
    result = analyze_positioning([_centered_box(100)], _W, _H)  # ratio 0.01
    assert FaceIssue.TOO_FAR in result.issues
    assert result.ready is False


def test_face_too_close() -> None:
    result = analyze_positioning([_centered_box(800)], _W, _H)  # ratio 0.64
    assert FaceIssue.TOO_CLOSE in result.issues


def test_face_off_center() -> None:
    box = FaceBox(x=0, y=0, width=300, height=300)  # centre at (150, 150)
    result = analyze_positioning([box], _W, _H)
    assert FaceIssue.OFF_CENTER in result.issues


def test_multiple_faces_flagged() -> None:
    result = analyze_positioning([_centered_box(300), _centered_box(280)], _W, _H)
    assert FaceIssue.MULTIPLE_FACES in result.issues


def test_multiple_faces_allowed_when_configured() -> None:
    params = PositioningParams(allow_multiple_faces=True)
    result = analyze_positioning([_centered_box(300), _centered_box(280)], _W, _H, params)
    assert FaceIssue.MULTIPLE_FACES not in result.issues


def test_require_face_false_is_ready_when_empty() -> None:
    params = PositioningParams(require_face=False)
    result = analyze_positioning([], _W, _H, params)
    assert result.ready is True


def test_largest_face_selects_biggest() -> None:
    small = FaceBox(x=0, y=0, width=100, height=100)
    big = FaceBox(x=0, y=0, width=300, height=300)
    assert largest_face([small, big]) is big
    assert largest_face([]) is None
