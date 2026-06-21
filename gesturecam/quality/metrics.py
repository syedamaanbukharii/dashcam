"""Frame quality metrics (brightness / exposure) and a value object that
bundles the per-frame quality signals used by the best-shot engine.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .blur import to_gray, variance_of_laplacian


def mean_brightness(image: NDArray[np.generic]) -> float:
    """Mean luma in the ``[0, 255]`` range."""
    return float(to_gray(image).mean())


def is_underexposed(image: NDArray[np.generic], low: float = 40.0) -> bool:
    return mean_brightness(image) < low


def is_overexposed(image: NDArray[np.generic], high: float = 215.0) -> bool:
    return mean_brightness(image) > high


def exposure_ok(image: NDArray[np.generic], low: float = 40.0, high: float = 215.0) -> bool:
    """True when the mean brightness sits within a comfortable range."""
    brightness = mean_brightness(image)
    return low <= brightness <= high


@dataclass(frozen=True, slots=True)
class FrameQuality:
    """All quality signals for a candidate frame, as used in scoring."""

    sharpness: float
    brightness: float
    face_visible: float = 0.0
    smile: float = 0.0
    eyes_open: float = 0.0

    @classmethod
    def from_image(
        cls,
        image: NDArray[np.generic],
        *,
        face_visible: float = 0.0,
        smile: float = 0.0,
        eyes_open: float = 0.0,
    ) -> FrameQuality:
        """Build the image-only metrics, filling in any supplied face signals."""
        return cls(
            sharpness=variance_of_laplacian(image),
            brightness=mean_brightness(image),
            face_visible=face_visible,
            smile=smile,
            eyes_open=eyes_open,
        )
