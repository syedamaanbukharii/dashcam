"""Data model for a stored capture."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CaptureRecord:
    """A row in the captures table.

    ``id`` is ``None`` before the record has been inserted. ``metadata`` is a
    free-form dictionary persisted as a JSON string.
    """

    filename: str
    path: str
    media_type: str  # "photo" or "video"
    created_at: str
    score: float = 0.0
    width: int = 0
    height: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None

    def metadata_json(self) -> str:
        return json.dumps(self.metadata, ensure_ascii=False)

    @staticmethod
    def parse_metadata(raw: str | None) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}
