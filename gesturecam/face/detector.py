"""Face detection and mesh landmarks via MediaPipe Tasks.

As with the hand detector, MediaPipe is imported lazily and the concrete
implementation sits behind a :class:`FaceDetector` protocol so the application
depends only on the abstraction. The detector returns pixel-space
:class:`~gesturecam.face.types.FaceBox` objects plus, when requested, the raw
mesh landmark array used by :mod:`gesturecam.face.mesh`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

from ..errors import DependencyError, MissingModelError
from ..logging_setup import get_logger
from .types import FaceBox

logger = get_logger(__name__)


@dataclass(slots=True)
class FaceDetection:
    """A detected face: its box and (optionally) its mesh landmarks."""

    box: FaceBox
    mesh: NDArray[np.float64] | None = None


@runtime_checkable
class FaceDetector(Protocol):
    """Detects faces (and optional mesh) in a BGR frame."""

    def detect(self, frame_bgr: NDArray[np.uint8], timestamp_ms: int) -> list[FaceDetection]: ...

    def close(self) -> None: ...


class MediaPipeFaceDetector:
    """Face detector backed by the MediaPipe Face Landmarker (video mode).

    The Face Landmarker yields both a bounding region and dense mesh landmarks,
    so a single model covers detection, eye-openness and smile analysis.
    """

    def __init__(
        self,
        model_path: str,
        *,
        max_faces: int = 2,
        min_detection_confidence: float = 0.5,
    ) -> None:
        try:
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision as mp_vision
        except ImportError as exc:  # pragma: no cover - requires mediapipe
            raise DependencyError(
                "mediapipe is required for face detection. Install it with "
                "'pip install mediapipe'."
            ) from exc

        import os

        if not os.path.exists(model_path):
            raise MissingModelError(f"face landmarker model not found at {model_path}")

        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_faces=max_faces,
            min_face_detection_confidence=min_detection_confidence,
        )
        self._landmarker = mp_vision.FaceLandmarker.create_from_options(options)
        logger.info("MediaPipe face detector initialised (max_faces=%d)", max_faces)

    def detect(
        self, frame_bgr: NDArray[np.uint8], timestamp_ms: int
    ) -> list[FaceDetection]:  # pragma: no cover - requires mediapipe + camera
        import cv2
        import mediapipe as mp

        height, width = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

        detections: list[FaceDetection] = []
        for face in result.face_landmarks:
            mesh = np.array([[p.x, p.y, p.z] for p in face], dtype=np.float64)
            xs = mesh[:, 0] * width
            ys = mesh[:, 1] * height
            x0, y0 = int(xs.min()), int(ys.min())
            x1, y1 = int(xs.max()), int(ys.max())
            box = FaceBox(x=x0, y=y0, width=max(1, x1 - x0), height=max(1, y1 - y0))
            detections.append(FaceDetection(box=box, mesh=mesh))
        return detections

    def close(self) -> None:  # pragma: no cover - requires mediapipe
        self._landmarker.close()
