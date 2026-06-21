"""Tests for the pure gesture classifier using synthetic landmark hands.

The :func:`make_hand` helper builds anatomically plausible ``(21, 3)`` landmark
arrays in normalised image coordinates (``y`` grows downward), letting us assert
that each canonical pose classifies correctly with a usable confidence — all
without a camera or MediaPipe.
"""

from __future__ import annotations

import numpy as np

from gesturecam.gestures import landmarks as lm
from gesturecam.gestures.classifier import classify_hand, compute_finger_states
from gesturecam.gestures.types import Gesture

_FINGER_X = {"index": 0.42, "middle": 0.50, "ring": 0.58, "pinky": 0.66}
_FINGER_IDX = {
    "index": (5, 6, 7, 8),
    "middle": (9, 10, 11, 12),
    "ring": (13, 14, 15, 16),
    "pinky": (17, 18, 19, 20),
}


def _finger_points(x: float, extended: bool) -> tuple[tuple[float, float], ...]:
    mcp = (x, 0.60)
    if extended:  # straight up: tip far above the knuckle
        return mcp, (x, 0.45), (x, 0.37), (x, 0.30)
    # curled: tip folds back down near the knuckle (small PIP angle)
    return mcp, (x, 0.52), (x, 0.57), (x, 0.61)


def make_hand(
    *,
    index: bool = False,
    middle: bool = False,
    ring: bool = False,
    pinky: bool = False,
    thumb_extended: bool = False,
    thumb_dir: str = "side",
    pinch: bool = False,
) -> np.ndarray:
    """Construct a synthetic ``(21, 3)`` landmark array for a pose."""
    points = np.zeros((21, 3), dtype=np.float64)
    points[lm.WRIST] = (0.50, 0.90, 0.0)

    states = {"index": index, "middle": middle, "ring": ring, "pinky": pinky}
    for name, (m, p, d, t) in _FINGER_IDX.items():
        mcp, pip, dip, tip = _finger_points(_FINGER_X[name], states[name])
        points[m] = (*mcp, 0.0)
        points[p] = (*pip, 0.0)
        points[d] = (*dip, 0.0)
        points[t] = (*tip, 0.0)

    points[lm.THUMB_CMC] = (0.40, 0.66, 0.0)
    points[lm.THUMB_MCP] = (0.36, 0.60, 0.0)
    if thumb_dir == "up":
        points[lm.THUMB_IP] = (0.35, 0.45, 0.0)
        points[lm.THUMB_TIP] = (0.34, 0.30, 0.0)
    elif thumb_dir == "down":
        points[lm.THUMB_IP] = (0.35, 0.74, 0.0)
        points[lm.THUMB_TIP] = (0.34, 0.88, 0.0)
    elif thumb_extended:  # side, sticking out
        points[lm.THUMB_IP] = (0.26, 0.58, 0.0)
        points[lm.THUMB_TIP] = (0.16, 0.56, 0.0)
    else:  # side, folded across the palm (away from the index tip)
        points[lm.THUMB_CMC] = (0.40, 0.68, 0.0)
        points[lm.THUMB_MCP] = (0.37, 0.62, 0.0)
        points[lm.THUMB_IP] = (0.45, 0.60, 0.0)
        points[lm.THUMB_TIP] = (0.52, 0.66, 0.0)

    if pinch:  # bring the thumb tip to meet the index tip
        index_tip = points[lm.INDEX_TIP, :2]
        points[lm.THUMB_TIP] = (index_tip[0] + 0.01, index_tip[1] + 0.01, 0.0)
        points[lm.THUMB_IP] = (index_tip[0] + 0.06, index_tip[1] + 0.08, 0.0)

    return points


def _open_palm() -> np.ndarray:
    return make_hand(index=True, middle=True, ring=True, pinky=True, thumb_extended=True)


def _peace() -> np.ndarray:
    return make_hand(index=True, middle=True)


def _thumbs_up() -> np.ndarray:
    return make_hand(thumb_extended=True, thumb_dir="up")


def _thumbs_down() -> np.ndarray:
    return make_hand(thumb_extended=True, thumb_dir="down")


def _fist() -> np.ndarray:
    return make_hand()


def _pinch() -> np.ndarray:
    return make_hand(index=True, pinch=True)


def test_open_palm() -> None:
    result = classify_hand(_open_palm())
    assert result.gesture is Gesture.OPEN_PALM
    assert result.confidence > 0.5


def test_peace() -> None:
    result = classify_hand(_peace())
    assert result.gesture is Gesture.PEACE
    assert result.confidence > 0.5


def test_thumbs_up() -> None:
    result = classify_hand(_thumbs_up())
    assert result.gesture is Gesture.THUMBS_UP
    assert result.confidence > 0.5


def test_thumbs_down() -> None:
    result = classify_hand(_thumbs_down())
    assert result.gesture is Gesture.THUMBS_DOWN
    assert result.confidence > 0.5


def test_fist() -> None:
    result = classify_hand(_fist())
    assert result.gesture is Gesture.FIST
    assert result.confidence > 0.5


def test_pinch() -> None:
    result = classify_hand(_pinch())
    assert result.gesture is Gesture.PINCH
    assert result.confidence > 0.5


def test_finger_states_for_peace() -> None:
    from gesturecam.gestures.classifier import ClassifierParams

    states = compute_finger_states(_peace(), ClassifierParams())
    assert states.index is True
    assert states.middle is True
    assert states.ring is False
    assert states.pinky is False
    assert states.extended_count == 2


def test_low_confidence_returns_none() -> None:
    # A flat, degenerate hand (all landmarks identical) has no clear gesture.
    points = np.full((21, 3), 0.5, dtype=np.float64)
    points[lm.MIDDLE_MCP] = (0.5, 0.2, 0.0)  # give it a non-zero scale
    result = classify_hand(points)
    assert result.gesture is Gesture.NONE


def test_handedness_is_passed_through() -> None:
    result = classify_hand(_peace(), handedness="Left")
    assert result.handedness == "Left"
