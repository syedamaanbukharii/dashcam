"""Tests for shot scoring and best-shot selection."""

from __future__ import annotations

import pytest

from gesturecam.quality.metrics import FrameQuality
from gesturecam.quality.scoring import (
    ShotScoreWeights,
    best_index,
    normalise_brightness,
    normalise_sharpness,
    score_shot,
)


def test_best_index_picks_highest_sharpness() -> None:
    # Identical except sharpness; the sharpest should win.
    qualities = [
        FrameQuality(sharpness=100.0, brightness=128.0),
        FrameQuality(sharpness=600.0, brightness=128.0),
        FrameQuality(sharpness=300.0, brightness=128.0),
    ]
    assert best_index(qualities) == 1


def test_best_index_rewards_smile_and_open_eyes() -> None:
    base = {"sharpness": 400.0, "brightness": 128.0, "face_visible": 1.0}
    qualities = [
        FrameQuality(**base, smile=0.0, eyes_open=0.0),
        FrameQuality(**base, smile=1.0, eyes_open=1.0),
    ]
    assert best_index(qualities) == 1


def test_score_is_within_unit_interval() -> None:
    quality = FrameQuality(
        sharpness=500.0, brightness=128.0, face_visible=1.0, smile=1.0, eyes_open=1.0
    )
    score = score_shot(quality)
    assert 0.0 <= score <= 1.0


def test_normalisation_helpers() -> None:
    assert normalise_sharpness(0.0) == 0.0
    assert normalise_sharpness(10_000.0) == 1.0  # clamped
    # Brightness peaks at mid-grey and is lower at the extremes.
    assert normalise_brightness(128.0) > normalise_brightness(0.0)
    assert normalise_brightness(128.0) > normalise_brightness(255.0)


def test_weights_total() -> None:
    assert abs(ShotScoreWeights().total() - 1.0) < 1e-9


def test_best_index_empty_raises() -> None:
    with pytest.raises(ValueError):
        best_index([])
