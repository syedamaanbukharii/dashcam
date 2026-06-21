"""Tests for blur detection (variance of the Laplacian)."""

from __future__ import annotations

import numpy as np

from gesturecam.quality.blur import is_blurry, to_gray, variance_of_laplacian


def _checkerboard(size: int = 64, cell: int = 4) -> np.ndarray:
    """High-frequency black/white checkerboard — very 'sharp'."""
    rows = (np.arange(size) // cell) % 2
    cols = (np.arange(size) // cell) % 2
    pattern = np.bitwise_xor.outer(rows, cols).astype(np.uint8) * 255
    return np.stack([pattern] * 3, axis=-1)


def _flat(size: int = 64, value: int = 128) -> np.ndarray:
    return np.full((size, size, 3), value, dtype=np.uint8)


def _smooth_gradient(size: int = 64) -> np.ndarray:
    row = np.linspace(0, 255, size, dtype=np.float64)
    gray = np.tile(row, (size, 1)).astype(np.uint8)
    return np.stack([gray] * 3, axis=-1)


def test_sharp_has_higher_variance_than_flat() -> None:
    assert variance_of_laplacian(_checkerboard()) > variance_of_laplacian(_flat())


def test_sharp_beats_smooth_gradient() -> None:
    assert variance_of_laplacian(_checkerboard()) > variance_of_laplacian(_smooth_gradient())


def test_flat_image_is_blurry() -> None:
    assert is_blurry(_flat(), threshold=100.0) is True


def test_checkerboard_is_not_blurry() -> None:
    assert is_blurry(_checkerboard(), threshold=100.0) is False


def test_to_gray_accepts_2d_and_3d() -> None:
    gray2d = np.full((10, 10), 50, dtype=np.uint8)
    color = np.full((10, 10, 3), 50, dtype=np.uint8)
    assert to_gray(gray2d).shape == (10, 10)
    assert to_gray(color).shape == (10, 10)


def test_tiny_image_returns_zero_variance() -> None:
    assert variance_of_laplacian(np.zeros((2, 2, 3), dtype=np.uint8)) == 0.0
