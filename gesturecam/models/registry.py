"""Registry of the MediaPipe model assets the app depends on.

Models are not bundled; they are fetched once from Google's public MediaPipe
model storage (the only network access the app ever performs) and cached under
the platform models directory. Each :class:`ModelSpec` records where to download
it and where it lives locally.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .. import paths

_BASE = "https://storage.googleapis.com/mediapipe-models"


@dataclass(frozen=True, slots=True)
class ModelSpec:
    """A downloadable model asset."""

    key: str
    filename: str
    url: str
    description: str

    def local_path(self) -> Path:
        return paths.models_dir() / self.filename


HAND_LANDMARKER = ModelSpec(
    key="hand_landmarker",
    filename="hand_landmarker.task",
    url=f"{_BASE}/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
    description="MediaPipe Hand Landmarker (21 landmarks, up to 2 hands).",
)

FACE_LANDMARKER = ModelSpec(
    key="face_landmarker",
    filename="face_landmarker.task",
    url=f"{_BASE}/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
    description="MediaPipe Face Landmarker (dense mesh for framing/eyes/smile).",
)

ALL_MODELS: tuple[ModelSpec, ...] = (HAND_LANDMARKER, FACE_LANDMARKER)


def model_by_key(key: str) -> ModelSpec:
    for spec in ALL_MODELS:
        if spec.key == key:
            return spec
    raise KeyError(f"unknown model key: {key!r}")
