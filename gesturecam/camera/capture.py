"""Threaded, non-blocking camera capture.

OpenCV's ``VideoCapture.read`` is a blocking call. To keep the UI responsive we
run it on a dedicated daemon thread that always holds only the *latest* frame;
consumers grab whatever is most recent and never block waiting for I/O. OpenCV
is imported lazily so this module can be imported without the dependency
installed.
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from ..config.schema import CameraConfig
from ..errors import CameraUnavailableError
from ..logging_setup import get_logger
from .frame import Frame

if TYPE_CHECKING:  # pragma: no cover - typing only
    import cv2

logger = get_logger(__name__)


class CameraStream:
    """Background reader that always exposes the most recent frame.

    The class is a context manager; entering it opens the device and starts the
    reader thread, exiting releases everything. :meth:`read` returns the latest
    :class:`Frame` or ``None`` if no frame has arrived yet.
    """

    def __init__(self, config: CameraConfig, *, read_timeout: float = 5.0) -> None:
        self._config = config
        self._read_timeout = read_timeout
        self._capture: cv2.VideoCapture | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._frame: Frame | None = None
        self._running = threading.Event()
        self._frame_index = 0
        self._last_error: str | None = None

    # -- lifecycle ---------------------------------------------------------
    def open(self) -> None:
        """Open the capture device and start the background reader."""
        try:
            import cv2
        except ImportError as exc:  # pragma: no cover - requires opencv
            raise CameraUnavailableError(
                "OpenCV is required for camera capture. Install it with "
                "'pip install opencv-python'."
            ) from exc

        capture = cv2.VideoCapture(self._config.index)
        if not capture.isOpened():  # pragma: no cover - requires hardware
            capture.release()
            raise CameraUnavailableError(f"unable to open camera at index {self._config.index}")

        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._config.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._config.height)
        capture.set(cv2.CAP_PROP_FPS, self._config.fps)

        self._capture = capture
        self._running.set()
        self._thread = threading.Thread(target=self._reader_loop, name="camera-reader", daemon=True)
        self._thread.start()
        logger.info("Camera stream opened on index %d", self._config.index)

    def _reader_loop(self) -> None:  # pragma: no cover - requires hardware
        import cv2

        assert self._capture is not None
        backoff = 0.5
        while self._running.is_set():
            ok, image = self._capture.read()
            if not ok:
                self._last_error = "frame read failed"
                logger.warning("Camera read failed; attempting to recover")
                time.sleep(backoff)
                backoff = min(backoff * 2, 5.0)
                if not self._capture.isOpened():
                    self._capture.open(self._config.index)
                continue

            backoff = 0.5
            if self._config.mirror:
                image = cv2.flip(image, 1)

            self._frame_index += 1
            frame = Frame(
                image=np.ascontiguousarray(image),
                index=self._frame_index,
                timestamp_ms=int(time.monotonic() * 1000),
            )
            with self._lock:
                self._frame = frame

    def read(self) -> Frame | None:
        """Return the most recent frame, or ``None`` if none captured yet."""
        with self._lock:
            return self._frame

    def wait_for_frame(self, timeout: float | None = None) -> Frame:
        """Block until a frame is available or ``timeout`` seconds elapse."""
        deadline = time.monotonic() + (timeout if timeout is not None else self._read_timeout)
        while time.monotonic() < deadline:
            frame = self.read()
            if frame is not None:
                return frame
            time.sleep(0.01)
        raise CameraUnavailableError(  # pragma: no cover - requires hardware
            self._last_error or "timed out waiting for first camera frame"
        )

    def close(self) -> None:
        """Stop the reader thread and release the device."""
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        logger.info("Camera stream closed")

    # -- context manager ---------------------------------------------------
    def __enter__(self) -> CameraStream:
        self.open()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def capture_single_frame(config: CameraConfig) -> NDArray[np.uint8]:  # pragma: no cover
    """Open the camera briefly and return one frame (used by tests/tools)."""
    with CameraStream(config) as stream:
        return stream.wait_for_frame().image
