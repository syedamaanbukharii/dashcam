"""Tests for brightness and exposure metrics."""

from __future__ import annotations

import numpy as np

from gesturecam.quality.metrics import (
    FrameQuality,
    exposure_ok,
    is_overexposed,
    is_underexposed,
    mean_brightness,
)


def _solid(value: int) -> np.ndarray:
    return np.full((32, 32, 3), value, dtype=np.uint8)


def test_mean_brightness_black_and_white() -> None:
    assert mean_brightness(_solid(0)) == 0.0
    assert mean_brightness(_solid(255)) == 255.0


def test_mean_brightness_mid_grey() -> None:
    assert abs(mean_brightness(_solid(128)) - 128.0) < 1e-6


def test_exposure_classification() -> None:
    assert is_underexposed(_solid(10)) is True
    assert is_overexposed(_solid(250)) is True
    assert exposure_ok(_solid(128)) is True
    assert exposure_ok(_solid(10)) is False
    assert exposure_ok(_solid(250)) is False


def test_frame_quality_from_image_populates_fields() -> None:
    quality = FrameQuality.from_image(_solid(128), face_visible=1.0, smile=0.7, eyes_open=0.9)
    assert abs(quality.brightness - 128.0) < 1e-6
    assert quality.sharpness == 0.0  # flat image
    assert quality.face_visible == 1.0
    assert quality.smile == 0.7
    assert quality.eyes_open == 0.9
