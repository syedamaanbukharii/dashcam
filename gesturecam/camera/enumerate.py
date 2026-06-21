"""Discovery of available camera devices.

There is no portable API to enumerate cameras in OpenCV, so we probe a small
range of indices and report which ones open successfully. This is best-effort
and intended to populate a camera-selection dropdown in the UI.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..logging_setup import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class CameraInfo:
    """A camera that responded when probed."""

    index: int
    width: int
    height: int

    @property
    def label(self) -> str:
        return f"Camera {self.index} ({self.width}x{self.height})"


def enumerate_cameras(max_index: int = 5) -> list[CameraInfo]:  # pragma: no cover - hardware
    """Probe indices ``0..max_index-1`` and return those that open.

    Returns an empty list if OpenCV is unavailable or no cameras respond.
    """
    try:
        import cv2
    except ImportError:
        logger.warning("OpenCV not installed; cannot enumerate cameras")
        return []

    found: list[CameraInfo] = []
    for index in range(max_index):
        capture = cv2.VideoCapture(index)
        try:
            if not capture.isOpened():
                continue
            ok, frame = capture.read()
            if not ok or frame is None:
                continue
            height, width = frame.shape[:2]
            found.append(CameraInfo(index=index, width=int(width), height=int(height)))
        finally:
            capture.release()

    logger.info("Discovered %d camera(s)", len(found))
    return found
