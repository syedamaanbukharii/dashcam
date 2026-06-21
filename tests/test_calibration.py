"""Tests for the calibration service and profile."""

from __future__ import annotations

from gesturecam.gestures.classifier import ClassifierParams
from gesturecam.gestures.types import FingerStates, Gesture, GestureResult
from gesturecam.services.calibration import CalibrationProfile, CalibrationService

_FINGERS = FingerStates(False, True, True, False, False)


def _res(confidence: float, gesture: Gesture = Gesture.PEACE) -> GestureResult:
    return GestureResult(gesture, confidence, _FINGERS)


def test_empty_service_returns_base_profile() -> None:
    service = CalibrationService()
    profile = service.build_profile()
    assert profile.samples == 0
    assert profile.confidence_floor == ClassifierParams().confidence_floor


def test_profile_floor_tracks_observed_confidence() -> None:
    service = CalibrationService()
    for _ in range(6):
        service.add_sample(_res(0.8))
    profile = service.build_profile()
    assert profile.samples == 6
    # Floor sits a little below the mean (0.8 - 0.15 = 0.65), clamped to range.
    assert abs(profile.confidence_floor - 0.65) < 1e-6


def test_floor_is_clamped_to_sane_range() -> None:
    low = CalibrationService()
    for _ in range(3):
        low.add_sample(_res(0.10))
    assert low.build_profile().confidence_floor >= 0.30

    high = CalibrationService()
    for _ in range(3):
        high.add_sample(_res(0.99))
    assert high.build_profile().confidence_floor <= 0.70


def test_none_samples_are_ignored() -> None:
    service = CalibrationService()
    service.add_sample(_res(0.0, gesture=Gesture.NONE))
    assert service.total_samples == 0


def test_profile_to_params_applies_values() -> None:
    profile = CalibrationProfile(pinch_ratio=0.30, confidence_floor=0.55, samples=10)
    params = profile.to_params()
    assert params.pinch_ratio == 0.30
    assert params.confidence_floor == 0.55
    # Untouched fields keep their defaults.
    assert params.finger_straight_deg == ClassifierParams().finger_straight_deg


def test_profile_round_trips_through_disk(tmp_path) -> None:
    path = tmp_path / "calibration.json"
    profile = CalibrationProfile(pinch_ratio=0.31, confidence_floor=0.52, samples=7)
    CalibrationService.save  # noqa: B018 - sanity that attr exists

    service = CalibrationService()
    service.save(profile, path)
    loaded = CalibrationService.load(path)
    assert loaded.to_dict() == profile.to_dict()


def test_load_missing_file_returns_default(tmp_path) -> None:
    loaded = CalibrationService.load(tmp_path / "missing.json")
    assert loaded.samples == 0
