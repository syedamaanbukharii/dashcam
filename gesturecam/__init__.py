"""GestureCam Pro - touchless, AI-powered camera control via hand gestures.

This package is intentionally import-light at the top level: importing
``gesturecam`` must not pull in heavy optional dependencies (OpenCV,
MediaPipe, CustomTkinter, ...). Those are imported lazily by the concrete
implementations in their respective subpackages so that the pure-Python
core (configuration, gesture classification, quality metrics, storage)
remains importable and testable in any environment.
"""

from __future__ import annotations

__all__ = ["__version__", "APP_NAME", "APP_SLUG"]

__version__ = "1.0.0"

APP_NAME = "GestureCam Pro"
APP_SLUG = "gesturecam-pro"
