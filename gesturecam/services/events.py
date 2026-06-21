"""Events emitted by the engine and a thread-safe bus to deliver them.

The processing engine runs on a background thread; the UI runs on the main
thread. Rather than touch widgets from the worker, the engine publishes
immutable event objects onto a queue-backed :class:`EventBus`, and the UI drains
that queue from its own loop (e.g. Tk's ``after``). This keeps the threading
boundary explicit and one-directional.
"""

from __future__ import annotations

import queue
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from ..face.types import FacePositioning
from ..gestures.types import Action, Gesture

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..storage.models import CaptureRecord


@dataclass(slots=True)
class FrameReady:
    """A new preview frame is available (BGR image)."""

    image: NDArray[np.uint8]
    fps: float


@dataclass(slots=True)
class GestureDetected:
    """A stabilised gesture fired and mapped to an action."""

    gesture: Gesture
    action: Action


@dataclass(slots=True)
class PositioningUpdate:
    """Latest face-framing guidance for the user."""

    positioning: FacePositioning


@dataclass(slots=True)
class CountdownTick:
    """Countdown progressed; ``value`` of 0 means "now"."""

    value: int


@dataclass(slots=True)
class CaptureSaved:
    """A photo (or burst best-shot) was written and recorded."""

    record: CaptureRecord


@dataclass(slots=True)
class BurstProgress:
    """Progress within a burst capture."""

    captured: int
    total: int


@dataclass(slots=True)
class RecordingStateChanged:
    """Video recording started or stopped."""

    recording: bool
    path: Path | None = None


@dataclass(slots=True)
class DetectionLockChanged:
    """Gesture detection was locked or unlocked (Fist toggle)."""

    locked: bool


@dataclass(slots=True)
class StatusMessage:
    """A human-readable status line, optionally an error."""

    text: str
    level: str = "info"  # "info" | "warning" | "error"


@dataclass(slots=True)
class EngineStopped:
    """The engine loop has terminated."""

    reason: str = ""


Event = (
    FrameReady
    | GestureDetected
    | PositioningUpdate
    | CountdownTick
    | CaptureSaved
    | BurstProgress
    | RecordingStateChanged
    | DetectionLockChanged
    | StatusMessage
    | EngineStopped
)


@dataclass
class EventBus:
    """A thin, thread-safe publish/drain queue of :data:`Event` objects."""

    _queue: queue.Queue[Event] = field(default_factory=queue.Queue)

    def publish(self, event: Event) -> None:
        self._queue.put(event)

    def drain(self, max_items: int = 64) -> list[Event]:
        """Return up to ``max_items`` pending events without blocking."""
        events: list[Event] = []
        for _ in range(max_items):
            try:
                events.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return events
