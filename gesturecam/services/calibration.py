"""Per-user gesture calibration.

Hand proportions and how firmly people hold a gesture vary, so the wizard
collects a handful of :class:`~gesturecam.gestures.types.GestureResult` samples
for a few reference gestures and derives small threshold nudges. The result is a
:class:`CalibrationProfile` that persists to JSON and can be folded back into
:class:`~gesturecam.gestures.classifier.ClassifierParams`.

The aggregation maths is pure and unit-testable; only load/save touch disk.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import mean

from .. import paths
from ..errors import StorageError
from ..gestures.classifier import ClassifierParams
from ..gestures.types import Gesture, GestureResult
from ..logging_setup import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class CalibrationProfile:
    """Calibration adjustments derived from collected samples."""

    pinch_ratio: float = 0.35
    confidence_floor: float = 0.45
    samples: int = 0

    def to_params(self, base: ClassifierParams | None = None) -> ClassifierParams:
        """Return classifier params with the calibrated values applied."""
        base = base or ClassifierParams()
        return ClassifierParams(
            finger_straight_deg=base.finger_straight_deg,
            thumb_straight_deg=base.thumb_straight_deg,
            bend_floor_deg=base.bend_floor_deg,
            straight_ceiling_deg=base.straight_ceiling_deg,
            pinch_ratio=self.pinch_ratio,
            vertical_span=base.vertical_span,
            confidence_floor=self.confidence_floor,
        )

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> CalibrationProfile:
        base = cls()
        return cls(
            pinch_ratio=float(data.get("pinch_ratio", base.pinch_ratio)),  # type: ignore[arg-type]
            confidence_floor=float(
                data.get("confidence_floor", base.confidence_floor)  # type: ignore[arg-type]
            ),
            samples=int(data.get("samples", 0)),  # type: ignore[arg-type]
        )


@dataclass
class CalibrationService:
    """Collects gesture samples and derives a :class:`CalibrationProfile`."""

    base_params: ClassifierParams = field(default_factory=ClassifierParams)
    _confidences: dict[Gesture, list[float]] = field(default_factory=dict)

    def reset(self) -> None:
        self._confidences.clear()

    def add_sample(self, result: GestureResult) -> None:
        """Record one observed gesture result for the gesture it represents."""
        if result.is_none:
            return
        self._confidences.setdefault(result.gesture, []).append(result.confidence)

    @property
    def total_samples(self) -> int:
        return sum(len(values) for values in self._confidences.values())

    def build_profile(self) -> CalibrationProfile:
        """Derive a profile from the samples collected so far.

        The confidence floor is set a little below the mean observed confidence
        of successful gestures (clamped to a sane range), so a user whose
        gestures read consistently low still triggers reliably, without making
        the classifier so permissive that it fires spuriously.
        """
        all_conf = [c for values in self._confidences.values() for c in values]
        if not all_conf:
            return CalibrationProfile(
                pinch_ratio=self.base_params.pinch_ratio,
                confidence_floor=self.base_params.confidence_floor,
                samples=0,
            )

        avg = mean(all_conf)
        floor = _clamp(avg - 0.15, 0.30, 0.70)
        return CalibrationProfile(
            pinch_ratio=self.base_params.pinch_ratio,
            confidence_floor=round(floor, 3),
            samples=len(all_conf),
        )

    # -- persistence -------------------------------------------------------
    def save(self, profile: CalibrationProfile, path: Path | None = None) -> Path:
        target = path or paths.calibration_file()
        paths.ensure_dir(target.parent)
        try:
            target.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")
        except OSError as exc:
            raise StorageError(f"failed to save calibration to {target}: {exc}") from exc
        logger.info("Saved calibration profile to %s", target)
        return target

    @staticmethod
    def load(path: Path | None = None) -> CalibrationProfile:
        source = path or paths.calibration_file()
        if not source.exists():
            return CalibrationProfile()
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StorageError(f"failed to read calibration at {source}: {exc}") from exc
        return CalibrationProfile.from_dict(data)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
