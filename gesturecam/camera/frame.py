"""The :class:`Frame` value object passed around the pipeline."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray


@dataclass(slots=True)
class Frame:
    """A single captured frame plus light metadata.

    ``image`` is a BGR ``uint8`` array as produced by OpenCV. ``index`` is a
    monotonically increasing counter assigned by the capture thread and
    ``timestamp_ms`` is a millisecond timestamp suitable for MediaPipe's video
    running mode (which requires strictly increasing timestamps).
    """

    image: NDArray[np.uint8]
    index: int
    timestamp_ms: int = field(default_factory=lambda: int(time.monotonic() * 1000))

    @property
    def width(self) -> int:
        return int(self.image.shape[1])

    @property
    def height(self) -> int:
        return int(self.image.shape[0])
