"""Hand detection via the MediaPipe Tasks Hand Landmarker.

The concrete detector is isolated behind the :class:`HandDetector` protocol so
the rest of the application depends only on the abstraction (dependency
inversion). MediaPipe is imported lazily inside :class:`MediaPipeHandDetector`
so importing this module never requires MediaPipe to be installed - useful for
unit tests and for the pure-logic CI job.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

from ..errors import DependencyError, MissingModelError
from ..logging_setup import get_logger
from .classifier import ClassifierParams, classify_hand
from .landmarks import HandLandmarks
from .types import GestureResult

logger = get_logger(__name__)


@runtime_checkable
class HandDetector(Protocol):
    """Detects hands in a BGR frame and returns their landmarks."""

    def detect(self, frame_bgr: NDArray[np.uint8], timestamp_ms: int) -> list[HandLandmarks]:
        """Return landmarks for each detected hand (possibly empty)."""
        ...

    def close(self) -> None:
        """Release any underlying resources."""
        ...


class MediaPipeHandDetector:
    """Hand landmark detector backed by MediaPipe Tasks (video mode)."""

    def __init__(
        self,
        model_path: str,
        *,
        max_hands: int = 2,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        try:
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision as mp_vision
        except ImportError as exc:  # pragma: no cover - requires mediapipe
            raise DependencyError(
                "mediapipe is required for hand detection. Install it with "
                "'pip install mediapipe'."
            ) from exc

        import os

        if not os.path.exists(model_path):
            raise MissingModelError(f"hand landmarker model not found at {model_path}")

        self._mp_vision = mp_vision
        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._landmarker = mp_vision.HandLandmarker.create_from_options(options)
        logger.info("MediaPipe hand detector initialised (max_hands=%d)", max_hands)

    def detect(
        self, frame_bgr: NDArray[np.uint8], timestamp_ms: int
    ) -> list[HandLandmarks]:  # pragma: no cover - requires mediapipe + camera
        import cv2
        import mediapipe as mp

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

        hands: list[HandLandmarks] = []
        for index, hand in enumerate(result.hand_landmarks):
            points = np.array([[p.x, p.y, p.z] for p in hand], dtype=np.float64)
            handedness = "Unknown"
            score = 1.0
            if index < len(result.handedness) and result.handedness[index]:
                top = result.handedness[index][0]
                handedness = top.category_name
                score = float(top.score)
            hands.append(HandLandmarks(points=points, handedness=handedness, score=score))
        return hands

    def close(self) -> None:  # pragma: no cover - requires mediapipe
        self._landmarker.close()


def recognise_gestures(
    hands: list[HandLandmarks], params: ClassifierParams | None = None
) -> list[GestureResult]:
    """Classify every detected hand into a gesture result."""
    return [classify_hand(hand.points, hand.handedness, params) for hand in hands]
