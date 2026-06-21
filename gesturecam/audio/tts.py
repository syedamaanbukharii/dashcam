"""Offline text-to-speech feedback.

Speech is produced by ``pyttsx3`` on a dedicated worker thread so synthesis
never blocks the pipeline. If ``pyttsx3`` is unavailable or fails to initialise,
the engine degrades to a silent no-op rather than crashing the app, so voice is
always an optional enhancement.
"""

from __future__ import annotations

import queue
import threading
from typing import Protocol, runtime_checkable

from ..config.schema import AudioConfig
from ..logging_setup import get_logger

logger = get_logger(__name__)


@runtime_checkable
class Voice(Protocol):
    """Speaks short phrases and can be shut down cleanly."""

    def say(self, text: str) -> None: ...

    def shutdown(self) -> None: ...


class NullVoice:
    """A voice that does nothing - used when TTS is disabled or unavailable."""

    def say(self, text: str) -> None:
        logger.debug("Voice disabled; would have said %r", text)

    def shutdown(self) -> None:
        return None


class Pyttsx3Voice:
    """Threaded ``pyttsx3`` voice with a phrase queue."""

    def __init__(self, config: AudioConfig) -> None:
        self._config = config
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run, name="tts-worker", daemon=True)
        self._ready = threading.Event()
        self._failed = False
        self._thread.start()

    def _run(self) -> None:  # pragma: no cover - requires pyttsx3 + audio device
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", self._config.rate)
            engine.setProperty("volume", self._config.volume)
            if self._config.voice_id:
                engine.setProperty("voice", self._config.voice_id)
        except Exception:  # noqa: BLE001 - any failure means no audio
            logger.exception("Failed to initialise pyttsx3; voice disabled")
            self._failed = True
            self._ready.set()
            return

        self._ready.set()
        while True:
            text = self._queue.get()
            if text is None:
                break
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception:  # noqa: BLE001 - never let TTS crash the worker
                logger.exception("TTS playback failed for %r", text)
        engine.stop()

    def say(self, text: str) -> None:
        if self._failed:
            return
        self._queue.put(text)

    def shutdown(self) -> None:
        self._queue.put(None)
        self._thread.join(timeout=2.0)


def create_voice(config: AudioConfig) -> Voice:
    """Return a working voice, or :class:`NullVoice` if TTS cannot be used."""
    if not config.voice_enabled:
        return NullVoice()
    try:
        import pyttsx3  # noqa: F401
    except ImportError:
        logger.warning("pyttsx3 not installed; voice feedback disabled")
        return NullVoice()
    return Pyttsx3Voice(config)
