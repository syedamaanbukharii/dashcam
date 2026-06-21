"""Best-shot engine.

When burst mode is enabled the application captures several frames and must
decide which to keep. Each candidate is scored on five normalised signals and
combined with configurable weights:

* **sharpness**  - variance of the Laplacian, normalised against a reference.
* **brightness** - peaks for well-exposed mid-tones, falls off toward clipping.
* **face**       - whether a face is present and adequately sized.
* **smile**      - smile strength in ``[0, 1]``.
* **eyes**       - eye-openness in ``[0, 1]``.

The module is pure and unit-tested; it takes already-computed
:class:`~gesturecam.quality.metrics.FrameQuality` objects rather than raw
images so the scoring policy is independent of how the signals were measured.
"""

from __future__ import annotations

from dataclasses import dataclass

from .metrics import FrameQuality

# A sharpness variance at/above this maps to a normalised sharpness of 1.0.
DEFAULT_SHARPNESS_REFERENCE = 500.0


@dataclass(frozen=True, slots=True)
class ShotScoreWeights:
    """Relative importance of each quality signal in the final score."""

    sharpness: float = 0.35
    brightness: float = 0.20
    face: float = 0.20
    smile: float = 0.15
    eyes: float = 0.10

    def total(self) -> float:
        return self.sharpness + self.brightness + self.face + self.smile + self.eyes


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def normalise_sharpness(value: float, reference: float = DEFAULT_SHARPNESS_REFERENCE) -> float:
    """Map a raw Laplacian variance to ``[0, 1]``."""
    if reference <= 0:
        return 0.0
    return _clamp01(value / reference)


def normalise_brightness(value: float) -> float:
    """Map mean brightness to ``[0, 1]`` with a peak at mid-grey (128)."""
    return _clamp01(1.0 - abs(value - 128.0) / 128.0)


def score_shot(
    quality: FrameQuality,
    weights: ShotScoreWeights | None = None,
    *,
    sharpness_reference: float = DEFAULT_SHARPNESS_REFERENCE,
) -> float:
    """Return a single weighted quality score in ``[0, 1]`` for one frame."""
    weights = weights or ShotScoreWeights()
    total = weights.total()
    if total <= 0:
        return 0.0

    weighted = (
        weights.sharpness * normalise_sharpness(quality.sharpness, sharpness_reference)
        + weights.brightness * normalise_brightness(quality.brightness)
        + weights.face * _clamp01(quality.face_visible)
        + weights.smile * _clamp01(quality.smile)
        + weights.eyes * _clamp01(quality.eyes_open)
    )
    return weighted / total


def best_index(
    qualities: list[FrameQuality],
    weights: ShotScoreWeights | None = None,
    *,
    sharpness_reference: float = DEFAULT_SHARPNESS_REFERENCE,
) -> int:
    """Index of the highest-scoring frame. Raises on an empty list."""
    if not qualities:
        raise ValueError("cannot select the best shot from an empty list")
    scores = [score_shot(q, weights, sharpness_reference=sharpness_reference) for q in qualities]
    return max(range(len(scores)), key=lambda i: scores[i])
