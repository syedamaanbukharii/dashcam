"""Temporal gesture stabilisation.

A raw per-frame classification is far too jittery to drive actions directly, so
this module applies three guarantees the specification requires:

* **No single-frame triggers.** A gesture must be the majority of the last
  ``window_size`` frames *and* reach ``min_consistent_frames`` before it is
  ever confirmed.
* **Confidence gating.** Frames below ``min_confidence`` are treated as
  no-gesture so a weak, ambiguous reading cannot accumulate.
* **Debounce.** Once a gesture fires, the same gesture will not re-fire until
  the hand is cleared (returns to no-gesture) *and* ``cooldown_seconds`` have
  elapsed, preventing a held pose from spamming the action.

The stabiliser is time-injectable (``now`` is passed in by the caller) so its
behaviour is fully deterministic and unit-testable without sleeping.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass

from .types import Gesture, GestureResult


@dataclass(frozen=True, slots=True)
class StabilizerParams:
    """Tunable parameters for :class:`GestureStabilizer`."""

    window_size: int = 8
    min_consistent_frames: int = 5
    min_confidence: float = 0.6
    cooldown_seconds: float = 1.5

    def __post_init__(self) -> None:
        if self.window_size < 1:
            raise ValueError("window_size must be >= 1")
        if self.min_consistent_frames < 1:
            raise ValueError("min_consistent_frames must be >= 1")
        if self.min_consistent_frames > self.window_size:
            raise ValueError("min_consistent_frames cannot exceed window_size")


class GestureStabilizer:
    """Smooths raw gesture results into discrete, debounced trigger events."""

    def __init__(self, params: StabilizerParams | None = None) -> None:
        self._params = params or StabilizerParams()
        self._buffer: deque[Gesture] = deque(maxlen=self._params.window_size)
        self._active: Gesture = Gesture.NONE
        self._last_trigger_time: float = float("-inf")

    @property
    def active(self) -> Gesture:
        """The currently confirmed (held) gesture, or ``NONE``."""
        return self._active

    def reset(self) -> None:
        """Clear all history (e.g. when detection is locked or paused)."""
        self._buffer.clear()
        self._active = Gesture.NONE
        self._last_trigger_time = float("-inf")

    def update(self, result: GestureResult, now: float) -> Gesture | None:
        """Feed one frame's result.

        Returns the gesture if *this* frame confirms a brand-new trigger,
        otherwise ``None``. ``now`` is a monotonic timestamp in seconds.
        """
        gesture = (
            result.gesture if result.confidence >= self._params.min_confidence else Gesture.NONE
        )
        self._buffer.append(gesture)

        confirmed = self._dominant_gesture()

        if confirmed is Gesture.NONE:
            # Hand cleared: allow the next distinct gesture to fire again.
            self._active = Gesture.NONE
            return None

        if confirmed is self._active:
            # Same gesture still held - do not re-fire.
            return None

        triggered: Gesture | None = None
        if now - self._last_trigger_time >= self._params.cooldown_seconds:
            triggered = confirmed
            self._last_trigger_time = now
        self._active = confirmed
        return triggered

    def _dominant_gesture(self) -> Gesture:
        if not self._buffer:
            return Gesture.NONE
        counts = Counter(g for g in self._buffer if g is not Gesture.NONE)
        if not counts:
            return Gesture.NONE
        gesture, count = counts.most_common(1)[0]
        if count >= self._params.min_consistent_frames:
            return gesture
        return Gesture.NONE
