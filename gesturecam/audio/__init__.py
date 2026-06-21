"""Voice-feedback subsystem."""

from __future__ import annotations

from .tts import NullVoice, Voice, create_voice

__all__ = ["NullVoice", "Voice", "create_voice"]
