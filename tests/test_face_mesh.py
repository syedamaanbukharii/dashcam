"""Tests for face-mesh metrics (eye-aspect-ratio and smile ratio)."""

from __future__ import annotations

import numpy as np

from gesturecam.face import mesh


def _blank() -> np.ndarray:
    return np.zeros((478, 3), dtype=np.float64)


def _set_eye(points: np.ndarray, eye: tuple[int, ...], *, open_eye: bool) -> None:
    p1, p2, p3, p4, p5, p6 = eye
    # Corners define the horizontal span.
    points[p1, :2] = (0.0, 0.5)
    points[p4, :2] = (0.10, 0.5)
    if open_eye:
        points[p2, :2] = (0.03, 0.47)
        points[p6, :2] = (0.03, 0.53)
        points[p3, :2] = (0.07, 0.47)
        points[p5, :2] = (0.07, 0.53)
    else:  # lids together
        for idx in (p2, p3, p5, p6):
            points[idx, :2] = (0.05, 0.50)


def _set_mouth(points: np.ndarray, *, smiling: bool) -> None:
    if smiling:  # wide and short
        points[mesh.MOUTH_LEFT, :2] = (0.40, 0.70)
        points[mesh.MOUTH_RIGHT, :2] = (0.60, 0.70)
        points[mesh.MOUTH_TOP, :2] = (0.50, 0.69)
        points[mesh.MOUTH_BOTTOM, :2] = (0.50, 0.71)
    else:  # narrow and tall
        points[mesh.MOUTH_LEFT, :2] = (0.45, 0.70)
        points[mesh.MOUTH_RIGHT, :2] = (0.55, 0.70)
        points[mesh.MOUTH_TOP, :2] = (0.50, 0.66)
        points[mesh.MOUTH_BOTTOM, :2] = (0.50, 0.74)


def test_open_eyes_have_higher_ear_than_closed() -> None:
    open_pts = _blank()
    _set_eye(open_pts, mesh.LEFT_EYE, open_eye=True)
    _set_eye(open_pts, mesh.RIGHT_EYE, open_eye=True)

    closed_pts = _blank()
    _set_eye(closed_pts, mesh.LEFT_EYE, open_eye=False)
    _set_eye(closed_pts, mesh.RIGHT_EYE, open_eye=False)

    assert mesh.average_ear(open_pts) > mesh.average_ear(closed_pts)


def test_eyes_open_classification() -> None:
    open_pts = _blank()
    _set_eye(open_pts, mesh.LEFT_EYE, open_eye=True)
    _set_eye(open_pts, mesh.RIGHT_EYE, open_eye=True)
    assert mesh.eyes_open(open_pts) is True

    closed_pts = _blank()
    _set_eye(closed_pts, mesh.LEFT_EYE, open_eye=False)
    _set_eye(closed_pts, mesh.RIGHT_EYE, open_eye=False)
    assert mesh.eyes_open(closed_pts) is False


def test_smile_ratio_higher_for_wide_mouth() -> None:
    smiling = _blank()
    _set_mouth(smiling, smiling=True)
    neutral = _blank()
    _set_mouth(neutral, smiling=False)
    assert mesh.smile_ratio(smiling) > mesh.smile_ratio(neutral)


def test_is_smiling_classification() -> None:
    smiling = _blank()
    _set_mouth(smiling, smiling=True)
    assert mesh.is_smiling(smiling) is True

    neutral = _blank()
    _set_mouth(neutral, smiling=False)
    assert mesh.is_smiling(neutral) is False


def test_degenerate_inputs_are_safe() -> None:
    # All-zero landmarks must not raise (division guards return 0).
    blank = _blank()
    assert mesh.average_ear(blank) == 0.0
    assert mesh.smile_ratio(blank) == 0.0
