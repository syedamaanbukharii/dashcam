"""Hand-gesture recognition subsystem."""

from __future__ import annotations

from .classifier import ClassifierParams, classify_hand, compute_finger_states
from .landmarks import HandLandmarks
from .recognizer import HandDetector, recognise_gestures
from .stabilizer import GestureStabilizer, StabilizerParams
from .types import Action, FingerStates, Gesture, GestureResult

__all__ = [
    "Action",
    "ClassifierParams",
    "FingerStates",
    "Gesture",
    "GestureResult",
    "GestureStabilizer",
    "HandDetector",
    "HandLandmarks",
    "StabilizerParams",
    "classify_hand",
    "compute_finger_states",
    "recognise_gestures",
]
