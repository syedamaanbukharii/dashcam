"""Gesture-controlled video recording.

Frames are pushed onto a bounded queue and written to an MP4 by a dedicated
worker thread, so encoding never blocks the capture or UI threads. OpenCV is
imported lazily inside the worker.
"""

from __future__ import annotations

import datetime as _dt
import queue
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from ..errors import StorageError
from ..logging_setup import get_logger
from ..paths import ensure_dir

if TYPE_CHECKING:  # pragma: no cover - typing only
    import cv2

logger = get_logger(__name__)


def _timestamped_name(prefix: str = "video", suffix: str = ".mp4") -> str:
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{stamp}{suffix}"


class VideoRecorder:
    """Encodes pushed frames to a timestamped MP4 on a worker thread."""

    def __init__(self, output_dir: Path, *, fps: int = 30, queue_size: int = 120) -> None:
        self._output_dir = output_dir
        self._fps = max(1, fps)
        self._queue: queue.Queue[NDArray[np.uint8] | None] = queue.Queue(maxsize=queue_size)
        self._thread: threading.Thread | None = None
        self._writer: cv2.VideoWriter | None = None
        self._active = threading.Event()
        self._path: Path | None = None
        self._size: tuple[int, int] | None = None
        self._dropped = 0

    @property
    def is_recording(self) -> bool:
        return self._active.is_set()

    @property
    def output_path(self) -> Path | None:
        return self._path

    def start(self, frame_size: tuple[int, int]) -> Path:
        """Begin recording frames of ``(width, height)``; returns the file path."""
        if self._active.is_set():
            raise StorageError("recording already in progress")
        try:
            import cv2  # noqa: F401
        except ImportError as exc:  # pragma: no cover - requires opencv
            raise StorageError(
                "OpenCV is required for video recording. Install 'opencv-python'."
            ) from exc

        ensure_dir(self._output_dir)
        self._path = self._output_dir / _timestamped_name()
        self._size = frame_size
        self._dropped = 0
        self._active.set()
        self._thread = threading.Thread(target=self._worker, name="video-writer", daemon=True)
        self._thread.start()
        logger.info("Started recording to %s", self._path)
        return self._path

    def _worker(self) -> None:  # pragma: no cover - requires opencv
        import cv2

        assert self._path is not None and self._size is not None
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._writer = cv2.VideoWriter(str(self._path), fourcc, self._fps, self._size)
        if not self._writer.isOpened():
            logger.error("Failed to open video writer for %s", self._path)
            self._active.clear()
            return

        while True:
            item = self._queue.get()
            if item is None:
                break
            self._writer.write(item)
        self._writer.release()
        self._writer = None

    def write(self, image: NDArray[np.uint8]) -> None:
        """Queue a frame for encoding; silently drops if the queue is full."""
        if not self._active.is_set():
            return
        try:
            self._queue.put_nowait(image)
        except queue.Full:  # pragma: no cover - timing dependent
            self._dropped += 1

    def stop(self) -> Path | None:
        """Finish encoding and return the written file path."""
        if not self._active.is_set():
            return None
        self._active.clear()
        self._queue.put(None)
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        if self._dropped:  # pragma: no cover - timing dependent
            logger.warning("Dropped %d frame(s) during recording", self._dropped)
        logger.info("Stopped recording: %s", self._path)
        return self._path

    def __enter__(self) -> VideoRecorder:
        return self

    def __exit__(self, *exc: object) -> None:
        if self._active.is_set():
            self.stop()
