"""Application configuration: typed schema plus JSON persistence."""

from __future__ import annotations

from .manager import ConfigManager
from .schema import (
    AppConfig,
    AudioConfig,
    BackgroundConfig,
    BestShotConfig,
    BurstConfig,
    CameraConfig,
    CountdownConfig,
    EnhancementConfig,
    FaceConfig,
    GestureMappingConfig,
    QualityConfig,
    RecognitionConfig,
    StorageConfig,
)

__all__ = [
    "AppConfig",
    "AudioConfig",
    "BackgroundConfig",
    "BestShotConfig",
    "BurstConfig",
    "CameraConfig",
    "ConfigManager",
    "CountdownConfig",
    "EnhancementConfig",
    "FaceConfig",
    "GestureMappingConfig",
    "QualityConfig",
    "RecognitionConfig",
    "StorageConfig",
]
