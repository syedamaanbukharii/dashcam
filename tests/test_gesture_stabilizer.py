"""Tests for the temporal gesture stabiliser (deterministic, injected clock)."""

from __future__ import annotations

from gesturecam.gestures.stabilizer import GestureStabilizer, StabilizerParams
from gesturecam.gestures.types import FingerStates, Gesture, GestureResult

_DUMMY_FINGERS = FingerStates(False, False, False, False, False)


def _res(gesture: Gesture, confidence: float = 0.9) -> GestureResult:
    return GestureResult(gesture, confidence, _DUMMY_FINGERS)


def _params() -> StabilizerParams:
    return StabilizerParams(
        window_size=8,
        min_consistent_frames=3,
        min_confidence=0.6,
        cooldown_seconds=1.0,
    )


def test_fires_once_after_enough_consistent_frames() -> None:
    stab = GestureStabilizer(_params())
    outcomes = [stab.update(_res(Gesture.PEACE), t) for t in (0.0, 0.1, 0.2)]
    assert outcomes[0] is None
    assert outcomes[1] is None
    assert outcomes[2] is Gesture.PEACE


def test_held_gesture_does_not_refire() -> None:
    stab = GestureStabilizer(_params())
    for t in (0.0, 0.1, 0.2):
        stab.update(_res(Gesture.PEACE), t)
    # Continuing to hold the same gesture must not trigger again.
    assert stab.update(_res(Gesture.PEACE), 0.3) is None
    assert stab.update(_res(Gesture.PEACE), 0.4) is None


def test_single_frame_spike_is_ignored() -> None:
    stab = GestureStabilizer(_params())
    assert stab.update(_res(Gesture.FIST), 0.0) is None
    # Surrounded by no-gesture frames it never reaches the consistency floor.
    for t in (0.1, 0.2, 0.3):
        assert stab.update(_res(Gesture.NONE, confidence=0.0), t) is None


def test_low_confidence_frames_never_trigger() -> None:
    stab = GestureStabilizer(_params())
    fired = [stab.update(_res(Gesture.PEACE, confidence=0.3), t / 10.0) for t in range(10)]
    assert all(outcome is None for outcome in fired)


def test_refires_after_clearing_and_cooldown() -> None:
    stab = GestureStabilizer(_params())
    for t in (0.0, 0.1, 0.2):
        stab.update(_res(Gesture.PEACE), t)  # fires at 0.2

    # Hand leaves the frame: a run of no-gesture frames clears the buffer.
    for t in range(3, 11):
        stab.update(_res(Gesture.NONE, confidence=0.0), t / 10.0)

    # Well after the cooldown, the same gesture can fire again.
    again = [stab.update(_res(Gesture.PEACE), t) for t in (2.0, 2.1, 2.2)]
    assert again[-1] is Gesture.PEACE


def test_cooldown_blocks_immediate_switch() -> None:
    stab = GestureStabilizer(_params())
    for t in (0.0, 0.1, 0.2):
        stab.update(_res(Gesture.PEACE), t)  # fires PEACE at 0.2

    # Switching gesture inside the cooldown window does not trigger.
    switched = [stab.update(_res(Gesture.FIST), t) for t in (0.3, 0.4, 0.5)]
    assert all(outcome is None for outcome in switched)


def test_reset_clears_state() -> None:
    stab = GestureStabilizer(_params())
    for t in (0.0, 0.1, 0.2):
        stab.update(_res(Gesture.PEACE), t)
    stab.reset()
    assert stab.active is Gesture.NONE
    # After reset the gesture can fire again immediately (cooldown cleared).
    fired = [stab.update(_res(Gesture.PEACE), t) for t in (5.0, 5.1, 5.2)]
    assert fired[-1] is Gesture.PEACE
