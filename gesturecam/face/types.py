"""Value objects for the face subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FaceIssue(str, Enum):
    """A reason a frame is not ready for capture, based on the face."""

    NO_FACE = "no_face"
    MULTIPLE_FACES = "multiple_faces"
    TOO_CLOSE = "too_close"
    TOO_FAR = "too_far"
    OFF_CENTER = "off_center"
    EYES_CLOSED = "eyes_closed"
    NOT_SMILING = "not_smiling"


# Short, friendly guidance shown to the user for each issue.
GUIDANCE: dict[FaceIssue, str] = {
    FaceIssue.NO_FACE: "Step into the frame",
    FaceIssue.MULTIPLE_FACES: "Only one person, please",
    FaceIssue.TOO_CLOSE: "Move back a little",
    FaceIssue.TOO_FAR: "Come a bit closer",
    FaceIssue.OFF_CENTER: "Center yourself in the frame",
    FaceIssue.EYES_CLOSED: "Open your eyes",
    FaceIssue.NOT_SMILING: "Give us a smile",
}


@dataclass(frozen=True, slots=True)
class FaceBox:
    """An axis-aligned face bounding box in pixel coordinates."""

    x: int
    y: int
    width: int
    height: int
    score: float = 1.0

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2.0, self.y + self.height / 2.0)


@dataclass(frozen=True, slots=True)
class FacePositioning:
    """The verdict of analysing one or more faces against framing rules."""

    ready: bool
    face_count: int
    issues: list[FaceIssue] = field(default_factory=list)

    @property
    def guidance(self) -> str:
        """The single most relevant guidance message, or a ready message."""
        if self.ready:
            return "Looking good!"
        if self.issues:
            return GUIDANCE.get(self.issues[0], "Adjust your position")
        return "Adjust your position"
