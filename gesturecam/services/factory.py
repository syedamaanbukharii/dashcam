"""Construction of the application's heavy, side-effecting dependencies.

Centralising construction here keeps wiring out of the engine and UI (dependency
inversion: they receive ready-made objects) and gives one place to swap real
implementations for fakes in tests. Nothing heavy is imported at module load;
each ``build_*`` method pulls in what it needs only when called.
"""

from __future__ import annotations

from pathlib import Path

from .. import paths
from ..audio.tts import Voice, create_voice
from ..camera.capture import CameraStream
from ..config.schema import AppConfig
from ..face.detector import FaceDetector
from ..gestures.recognizer import HandDetector
from ..logging_setup import get_logger
from ..storage.database import CaptureDatabase
from ..video.recorder import VideoRecorder

logger = get_logger(__name__)


class DependencyFactory:
    """Builds cameras, detectors, voice, recorder and database on demand."""

    def __init__(self, config: AppConfig, *, allow_model_download: bool = True) -> None:
        self._config = config
        self._allow_model_download = allow_model_download

    def build_camera(self) -> CameraStream:
        return CameraStream(self._config.camera)

    def build_hand_detector(self) -> HandDetector:
        from ..gestures.recognizer import MediaPipeHandDetector
        from ..models import HAND_LANDMARKER, ensure_model

        model_path = ensure_model(HAND_LANDMARKER, allow_download=self._allow_model_download)
        recognition = self._config.recognition
        return MediaPipeHandDetector(
            str(model_path),
            max_hands=recognition.max_hands,
            min_detection_confidence=recognition.min_detection_confidence,
            min_tracking_confidence=recognition.min_tracking_confidence,
        )

    def build_face_detector(self) -> FaceDetector:
        from ..face.detector import MediaPipeFaceDetector
        from ..models import FACE_LANDMARKER, ensure_model

        model_path = ensure_model(FACE_LANDMARKER, allow_download=self._allow_model_download)
        return MediaPipeFaceDetector(
            str(model_path),
            max_faces=2 if self._config.face.allow_multiple_faces else 1,
            min_detection_confidence=self._config.recognition.min_detection_confidence,
        )

    def build_voice(self) -> Voice:
        return create_voice(self._config.audio)

    def build_recorder(self) -> VideoRecorder:
        return VideoRecorder(self._video_dir(), fps=self._config.camera.fps)

    def build_database(self) -> CaptureDatabase:
        return CaptureDatabase(paths.database_file())

    def _video_dir(self) -> Path:
        folder = Path(self._config.storage.save_folder) / "videos"
        paths.ensure_dir(folder)
        return folder
