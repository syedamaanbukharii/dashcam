"""Face positioning analysis.

Given the face boxes returned by the detector and the frame dimensions, decide
whether framing is acceptable and, if not, why. This is pure geometry and has
no detector or camera dependency, so it is fully unit-testable.

Sizing is judged by the fraction of the frame area the largest face occupies;
centering by how far the face centre sits from the frame centre, as a fraction
of the frame dimensions.
"""

from __future__ import annotations

from dataclasses import dataclass

from .types import FaceBox, FaceIssue, FacePositioning


@dataclass(frozen=True, slots=True)
class PositioningParams:
    """Thresholds for the framing checks."""

    require_face: bool = True
    allow_multiple_faces: bool = False
    min_face_area_ratio: float = 0.03
    """Below this fraction of the frame, the face is 'too far'."""
    max_face_area_ratio: float = 0.55
    """Above this fraction of the frame, the face is 'too close'."""
    center_tolerance: float = 0.22
    """Max allowed centre offset as a fraction of width/height."""


def largest_face(faces: list[FaceBox]) -> FaceBox | None:
    """Return the face with the greatest area, or ``None`` if there are none."""
    if not faces:
        return None
    return max(faces, key=lambda f: f.area)


def analyze_positioning(
    faces: list[FaceBox],
    frame_width: int,
    frame_height: int,
    params: PositioningParams | None = None,
) -> FacePositioning:
    """Evaluate framing rules and return a :class:`FacePositioning` verdict."""
    params = params or PositioningParams()
    issues: list[FaceIssue] = []

    if not faces:
        if params.require_face:
            issues.append(FaceIssue.NO_FACE)
        return FacePositioning(ready=not params.require_face, face_count=0, issues=issues)

    if len(faces) > 1 and not params.allow_multiple_faces:
        issues.append(FaceIssue.MULTIPLE_FACES)

    frame_area = max(1, frame_width * frame_height)
    face = largest_face(faces)
    assert face is not None  # non-empty checked above
    area_ratio = face.area / frame_area

    if area_ratio > params.max_face_area_ratio:
        issues.append(FaceIssue.TOO_CLOSE)
    elif area_ratio < params.min_face_area_ratio:
        issues.append(FaceIssue.TOO_FAR)

    cx, cy = face.center
    dx = abs(cx - frame_width / 2.0) / max(1.0, frame_width)
    dy = abs(cy - frame_height / 2.0) / max(1.0, frame_height)
    if dx > params.center_tolerance or dy > params.center_tolerance:
        issues.append(FaceIssue.OFF_CENTER)

    return FacePositioning(ready=not issues, face_count=len(faces), issues=issues)
