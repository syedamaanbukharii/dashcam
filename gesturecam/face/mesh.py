"""Face-mesh derived metrics: eye openness and smile.

These operate on the 478-point MediaPipe Face Mesh landmark array (a
``(N, 3)`` float array of normalised coordinates) and are pure functions, so
they can be unit-tested with synthetic landmark arrays.

* **Eye openness** uses the Eye Aspect Ratio (EAR): the ratio of vertical eye
  opening to horizontal eye width. EAR collapses toward zero as the eye closes.
* **Smile** uses the ratio of mouth width to mouth height; a smile widens and
  flattens the mouth, raising the ratio.
"""

from __future__ import annotations

from typing import Final

import numpy as np
from numpy.typing import NDArray

# MediaPipe Face Mesh landmark indices.
# Each eye uses six points: two horizontal corners and two vertical pairs.
LEFT_EYE: Final[tuple[int, int, int, int, int, int]] = (33, 160, 158, 133, 153, 144)
RIGHT_EYE: Final[tuple[int, int, int, int, int, int]] = (362, 385, 387, 263, 373, 380)

# Mouth: left/right corners and upper/lower lip midpoints.
MOUTH_LEFT: Final = 61
MOUTH_RIGHT: Final = 291
MOUTH_TOP: Final = 13
MOUTH_BOTTOM: Final = 14

# Empirically reasonable defaults; tunable via configuration.
DEFAULT_EAR_THRESHOLD: Final = 0.18
DEFAULT_SMILE_THRESHOLD: Final = 0.55


def _norm(points: NDArray[np.float64], a: int, b: int) -> float:
    return float(np.linalg.norm(points[a, :2] - points[b, :2]))


def eye_aspect_ratio(points: NDArray[np.float64], eye: tuple[int, ...]) -> float:
    """Compute the EAR for one eye from its six landmark indices."""
    p1, p2, p3, p4, p5, p6 = eye
    horizontal = _norm(points, p1, p4)
    if horizontal <= 1e-9:
        return 0.0
    vertical = _norm(points, p2, p6) + _norm(points, p3, p5)
    return vertical / (2.0 * horizontal)


def average_ear(points: NDArray[np.float64]) -> float:
    """Mean EAR across both eyes."""
    return 0.5 * (eye_aspect_ratio(points, LEFT_EYE) + eye_aspect_ratio(points, RIGHT_EYE))


def eyes_open(points: NDArray[np.float64], threshold: float = DEFAULT_EAR_THRESHOLD) -> bool:
    """True when both eyes appear open."""
    return average_ear(points) >= threshold


def smile_ratio(points: NDArray[np.float64]) -> float:
    """Mouth width-to-height ratio (larger => more smile-like)."""
    width = _norm(points, MOUTH_LEFT, MOUTH_RIGHT)
    height = _norm(points, MOUTH_TOP, MOUTH_BOTTOM)
    if width <= 1e-9:
        return 0.0
    # Invert so a wide, flat mouth yields a high score; height/width is small
    # for a smile, so 1 - (height/width) trends toward 1.
    return float(max(0.0, 1.0 - (height / width)))


def is_smiling(points: NDArray[np.float64], threshold: float = DEFAULT_SMILE_THRESHOLD) -> bool:
    """True when the smile ratio exceeds *threshold*."""
    return smile_ratio(points) >= threshold
