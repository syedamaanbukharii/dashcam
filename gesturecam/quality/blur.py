"""Blur detection.

Sharpness is estimated with the classic *variance of the Laplacian*: a sharp
image has strong high-frequency content (edges) and therefore a high-variance
Laplacian, whereas a blurry image is smooth and yields a low variance.

The Laplacian is computed with a pure-NumPy 4-neighbour discrete operator
rather than ``cv2.Laplacian`` so the metric has no OpenCV dependency and can be
exercised by unit tests in any environment. The numeric scale matches the
common OpenCV-based thresholds closely enough that the default
``blur_threshold`` in the configuration is meaningful.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

# Rec. 601 luma weights for BGR-ordered frames (OpenCV's native ordering).
_BGR_LUMA = np.array([0.114, 0.587, 0.299], dtype=np.float64)


def to_gray(image: NDArray[np.generic]) -> NDArray[np.float64]:
    """Convert a 2-D (grayscale) or 3-channel BGR image to a float gray array."""
    arr = np.asarray(image)
    if arr.ndim == 2:
        return arr.astype(np.float64)
    if arr.ndim == 3 and arr.shape[2] >= 3:
        return arr[..., :3].astype(np.float64) @ _BGR_LUMA
    raise ValueError(f"unsupported image shape for grayscale conversion: {arr.shape}")


def variance_of_laplacian(image: NDArray[np.generic]) -> float:
    """Return the variance of the discrete Laplacian of *image*.

    Higher means sharper. Border pixels are excluded to avoid wrap-around
    artefacts from the shifted differences.
    """
    gray = to_gray(image)
    if gray.shape[0] < 3 or gray.shape[1] < 3:
        return 0.0
    laplacian = (
        -4.0 * gray
        + np.roll(gray, 1, axis=0)
        + np.roll(gray, -1, axis=0)
        + np.roll(gray, 1, axis=1)
        + np.roll(gray, -1, axis=1)
    )
    interior = laplacian[1:-1, 1:-1]
    return float(interior.var())


def is_blurry(image: NDArray[np.generic], threshold: float) -> bool:
    """Return ``True`` when the image is below the sharpness *threshold*."""
    return variance_of_laplacian(image) < threshold
