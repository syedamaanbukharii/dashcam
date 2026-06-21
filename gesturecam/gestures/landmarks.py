"""Hand-landmark geometry helpers.

MediaPipe's Hand Landmarker returns 21 landmarks per hand. This module gives
those landmarks readable names and provides the small set of pure geometric
primitives (angles, distances, hand scale) that the gesture classifier needs.

Landmarks are represented as a ``(21, 3)`` float array of normalised
coordinates ``(x, y, z)`` where ``x``/``y`` are in ``[0, 1]`` relative to the
image and ``y`` grows downward (the usual image-coordinate convention).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
from numpy.typing import NDArray

# --- Landmark indices --------------------------------------------------------
WRIST: Final = 0
THUMB_CMC: Final = 1
THUMB_MCP: Final = 2
THUMB_IP: Final = 3
THUMB_TIP: Final = 4
INDEX_MCP: Final = 5
INDEX_PIP: Final = 6
INDEX_DIP: Final = 7
INDEX_TIP: Final = 8
MIDDLE_MCP: Final = 9
MIDDLE_PIP: Final = 10
MIDDLE_DIP: Final = 11
MIDDLE_TIP: Final = 12
RING_MCP: Final = 13
RING_PIP: Final = 14
RING_DIP: Final = 15
RING_TIP: Final = 16
PINKY_MCP: Final = 17
PINKY_PIP: Final = 18
PINKY_DIP: Final = 19
PINKY_TIP: Final = 20

NUM_LANDMARKS: Final = 21

# (mcp, pip, tip) joint triples for the four non-thumb fingers.
FINGER_JOINTS: Final[dict[str, tuple[int, int, int]]] = {
    "index": (INDEX_MCP, INDEX_PIP, INDEX_TIP),
    "middle": (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_TIP),
    "ring": (RING_MCP, RING_PIP, RING_TIP),
    "pinky": (PINKY_MCP, PINKY_PIP, PINKY_TIP),
}
THUMB_JOINTS: Final[tuple[int, int, int]] = (THUMB_MCP, THUMB_IP, THUMB_TIP)


@dataclass(slots=True)
class HandLandmarks:
    """Landmarks for a single detected hand."""

    points: NDArray[np.float64]
    handedness: str = "Unknown"
    score: float = 1.0

    def __post_init__(self) -> None:
        self.points = np.asarray(self.points, dtype=np.float64)
        if self.points.shape != (NUM_LANDMARKS, 3):
            raise ValueError(f"expected landmark array of shape (21, 3), got {self.points.shape}")


def angle_at(points: NDArray[np.float64], a: int, b: int, c: int) -> float:
    """Return the interior angle (degrees) at vertex *b* of triangle a-b-c.

    Uses only the in-plane (x, y) coordinates, which is robust to the noisy
    depth channel reported by MediaPipe.
    """
    pa = points[a, :2]
    pb = points[b, :2]
    pc = points[c, :2]
    v1 = pa - pb
    v2 = pc - pb
    n1 = float(np.linalg.norm(v1))
    n2 = float(np.linalg.norm(v2))
    if n1 == 0.0 or n2 == 0.0:
        return 0.0
    cosine = float(np.dot(v1, v2) / (n1 * n2))
    cosine = max(-1.0, min(1.0, cosine))
    return float(np.degrees(np.arccos(cosine)))


def distance(points: NDArray[np.float64], a: int, b: int) -> float:
    """Euclidean distance between landmarks *a* and *b* in the image plane."""
    return float(np.linalg.norm(points[a, :2] - points[b, :2]))


def hand_scale(points: NDArray[np.float64]) -> float:
    """A scale-invariant reference length for the hand.

    The wrist-to-middle-MCP distance is stable across hand orientations and is
    used to normalise pinch distances and vertical offsets.
    """
    scale = distance(points, WRIST, MIDDLE_MCP)
    return scale if scale > 1e-6 else 1e-6
