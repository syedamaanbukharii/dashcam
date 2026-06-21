"""Model asset registry and downloader."""

from __future__ import annotations

from .downloader import ensure_model, is_cached
from .registry import ALL_MODELS, FACE_LANDMARKER, HAND_LANDMARKER, ModelSpec, model_by_key

__all__ = [
    "ALL_MODELS",
    "FACE_LANDMARKER",
    "HAND_LANDMARKER",
    "ModelSpec",
    "ensure_model",
    "is_cached",
    "model_by_key",
]
