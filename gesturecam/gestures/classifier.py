"""Geometric gesture classifier.

This module is deliberately free of any camera, GUI or MediaPipe dependency: it
operates purely on a ``(21, 3)`` landmark array and NumPy, which makes it fully
unit-testable. The recogniser (:mod:`gesturecam.gestures.recognizer`) supplies
the landmarks at runtime; here we only turn geometry into a :class:`GestureResult`.

The approach is a *continuous-score* model rather than brittle if/else rules:
each candidate gesture receives a score in ``[0, 1]`` derived from how strongly
the relevant geometric criteria are satisfied, and the highest-scoring gesture
wins (subject to a confidence floor). This produces a meaningful confidence
value for the stabiliser to threshold on, and degrades gracefully near the
boundary between two similar poses.

Thresholds live in :class:`ClassifierParams` so the calibration wizard can tune
them per user without touching code.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from . import landmarks as lm
from .types import FingerStates, Gesture, GestureResult


@dataclass(frozen=True, slots=True)
class ClassifierParams:
    """Tunable thresholds for gesture classification."""

    finger_straight_deg: float = 155.0
    """A non-thumb finger counts as extended when its PIP angle exceeds this."""

    thumb_straight_deg: float = 145.0
    """The thumb counts as extended when its IP angle exceeds this."""

    bend_floor_deg: float = 90.0
    """Angle treated as fully bent (straightness score 0)."""

    straight_ceiling_deg: float = 175.0
    """Angle treated as fully straight (straightness score 1)."""

    pinch_ratio: float = 0.35
    """thumb-tip/index-tip distance over hand scale below which a pinch starts."""

    vertical_span: float = 0.55
    """Thumb tip vertical offset (over hand scale) for a full up/down score."""

    confidence_floor: float = 0.45
    """Minimum winning score required to report a gesture instead of NONE."""


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _straightness(angle_deg: float, params: ClassifierParams) -> float:
    """Map a joint angle to a 0..1 'straightness' score."""
    span = params.straight_ceiling_deg - params.bend_floor_deg
    if span <= 0:
        return 0.0
    return _clamp01((angle_deg - params.bend_floor_deg) / span)


def compute_finger_states(points: NDArray[np.float64], params: ClassifierParams) -> FingerStates:
    """Return boolean extended/folded state for every finger."""
    extended: dict[str, bool] = {}
    for name, (mcp, pip, tip) in lm.FINGER_JOINTS.items():
        extended[name] = lm.angle_at(points, mcp, pip, tip) >= params.finger_straight_deg
    thumb_angle = lm.angle_at(points, *lm.THUMB_JOINTS)
    return FingerStates(
        thumb=thumb_angle >= params.thumb_straight_deg,
        index=extended["index"],
        middle=extended["middle"],
        ring=extended["ring"],
        pinky=extended["pinky"],
    )


def _finger_scores(points: NDArray[np.float64], params: ClassifierParams) -> dict[str, float]:
    """Straightness score in 0..1 for each finger (including the thumb)."""
    scores: dict[str, float] = {}
    for name, (mcp, pip, tip) in lm.FINGER_JOINTS.items():
        scores[name] = _straightness(lm.angle_at(points, mcp, pip, tip), params)
    scores["thumb"] = _straightness(lm.angle_at(points, *lm.THUMB_JOINTS), params)
    return scores


def classify_hand(
    points: NDArray[np.float64],
    handedness: str = "Unknown",
    params: ClassifierParams | None = None,
) -> GestureResult:
    """Classify a single hand's landmarks into a :class:`GestureResult`."""
    params = params or ClassifierParams()
    points = np.asarray(points, dtype=np.float64)

    s = _finger_scores(points, params)
    folded = {name: 1.0 - value for name, value in s.items()}
    states = compute_finger_states(points, params)

    scale = lm.hand_scale(points)

    # Pinch: how close the thumb and index tips are, normalised by hand size.
    pinch_dist = lm.distance(points, lm.THUMB_TIP, lm.INDEX_TIP) / scale
    pinch_score = _clamp01((params.pinch_ratio - pinch_dist) / params.pinch_ratio)

    # Thumb vertical direction (image y grows downward => up means smaller y).
    thumb_dy = points[lm.THUMB_MCP, 1] - points[lm.THUMB_TIP, 1]
    up_score = _clamp01(thumb_dy / (params.vertical_span * scale))
    down_score = _clamp01(-thumb_dy / (params.vertical_span * scale))

    fingers_folded = (folded["index"] + folded["middle"] + folded["ring"] + folded["pinky"]) / 4.0
    fingers_open = (s["index"] + s["middle"] + s["ring"] + s["pinky"]) / 4.0

    scores: dict[Gesture, float] = {
        Gesture.OPEN_PALM: (fingers_open * 0.8 + s["thumb"] * 0.2),
        Gesture.PEACE: (
            (s["index"] + s["middle"]) / 2.0 * (folded["ring"] + folded["pinky"]) / 2.0
        ),
        Gesture.THUMBS_UP: s["thumb"] * up_score * fingers_folded,
        Gesture.THUMBS_DOWN: s["thumb"] * down_score * fingers_folded,
        # A pinch is the thumb/index meeting while the hand is not a closed fist.
        Gesture.PINCH: pinch_score * (0.4 + 0.6 * max(s["index"], s["thumb"])),
        # A fist is everything folded and the thumb not jutting up/down/out.
        Gesture.FIST: (fingers_folded * (1.0 - max(up_score, down_score)) * (1.0 - pinch_score)),
    }

    best = max(scores, key=lambda key: scores[key])
    confidence = scores[best]
    if confidence < params.confidence_floor:
        return GestureResult(Gesture.NONE, confidence, states, handedness)
    return GestureResult(best, _clamp01(confidence), states, handedness)
