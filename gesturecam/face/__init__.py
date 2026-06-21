"""Face detection, framing analysis and expression metrics."""

from __future__ import annotations

from .analysis import PositioningParams, analyze_positioning
from .detector import FaceDetection, FaceDetector
from .mesh import average_ear, eyes_open, is_smiling, smile_ratio
from .types import FaceBox, FaceIssue, FacePositioning

__all__ = [
    "FaceBox",
    "FaceDetection",
    "FaceDetector",
    "FaceIssue",
    "FacePositioning",
    "PositioningParams",
    "analyze_positioning",
    "average_ear",
    "eyes_open",
    "is_smiling",
    "smile_ratio",
]
