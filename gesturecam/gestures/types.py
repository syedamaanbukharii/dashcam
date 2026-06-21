"""Core gesture types: the recognised gestures, the actions they can trigger
and the value objects passed between the recogniser, classifier and stabiliser.

All enums subclass :class:`str` so they serialise transparently to JSON in the
configuration file and the calibration profile.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Gesture(str, Enum):
    """A hand gesture the system can recognise."""

    NONE = "none"
    PEACE = "peace"
    FIST = "fist"
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    PINCH = "pinch"
    OPEN_PALM = "open_palm"

    @property
    def label(self) -> str:
        """Human-friendly label, e.g. ``"Thumbs Up"``."""
        return self.value.replace("_", " ").title()


class Action(str, Enum):
    """An action a gesture can be mapped to."""

    NONE = "none"
    PHOTO = "photo"
    BURST = "burst"
    VIDEO_TOGGLE = "video_toggle"
    LOCK_DETECTION = "lock_detection"
    EXIT = "exit"

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").title()


@dataclass(frozen=True, slots=True)
class FingerStates:
    """Whether each finger is considered extended (straight)."""

    thumb: bool
    index: bool
    middle: bool
    ring: bool
    pinky: bool

    @property
    def extended_count(self) -> int:
        """Number of *non-thumb* fingers that are extended."""
        return sum((self.index, self.middle, self.ring, self.pinky))

    def as_tuple(self) -> tuple[bool, bool, bool, bool, bool]:
        return (self.thumb, self.index, self.middle, self.ring, self.pinky)


@dataclass(frozen=True, slots=True)
class GestureResult:
    """The classification result for a single hand on a single frame."""

    gesture: Gesture
    confidence: float
    fingers: FingerStates
    handedness: str = "Unknown"

    @property
    def is_none(self) -> bool:
        return self.gesture is Gesture.NONE
