"""Application services: orchestration, capture pipeline, calibration, events."""

from __future__ import annotations

from .calibration import CalibrationProfile, CalibrationService
from .capture_service import BurstOutcome, CaptureOutcome, CaptureService
from .engine import GestureEngine
from .events import (
    BurstProgress,
    CaptureSaved,
    CountdownTick,
    DetectionLockChanged,
    EngineStopped,
    Event,
    EventBus,
    FrameReady,
    GestureDetected,
    PositioningUpdate,
    RecordingStateChanged,
    StatusMessage,
)
from .factory import DependencyFactory

__all__ = [
    "BurstOutcome",
    "BurstProgress",
    "CalibrationProfile",
    "CalibrationService",
    "CaptureOutcome",
    "CaptureSaved",
    "CaptureService",
    "CountdownTick",
    "DependencyFactory",
    "DetectionLockChanged",
    "EngineStopped",
    "Event",
    "EventBus",
    "FrameReady",
    "GestureDetected",
    "GestureEngine",
    "PositioningUpdate",
    "RecordingStateChanged",
    "StatusMessage",
]
