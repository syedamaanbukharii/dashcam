"""The calibration wizard.

Walks the user through holding a few reference gestures, sampling the engine's
live (raw) classification results for each, then derives and saves a
:class:`~gesturecam.services.calibration.CalibrationProfile`. Sampling reads
:pyattr:`GestureEngine.latest_result` on a Tk timer, so it stays on the UI
thread and never blocks.
"""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ..gestures.types import Gesture
from ..logging_setup import get_logger
from ..services.calibration import CalibrationService
from ..services.engine import GestureEngine
from . import theme

logger = get_logger(__name__)

_STEPS: tuple[Gesture, ...] = (Gesture.PEACE, Gesture.THUMBS_UP, Gesture.PINCH)
_SAMPLES_PER_STEP = 20
_POLL_MS = 80


class CalibrationWindow(ctk.CTkToplevel):  # pragma: no cover - requires a display
    """Guided, multi-step calibration collector."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        engine: GestureEngine,
        *,
        on_saved: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self._engine = engine
        self._on_saved = on_saved
        self._service = CalibrationService()
        self._step = 0
        self._collected = 0
        self._collecting = False
        self._poll_id: str | None = None

        self.title("Calibration")
        self.geometry("440x320")
        self.grid_columnconfigure(0, weight=1)

        self._title = ctk.CTkLabel(self, text="", font=theme.font(theme.TITLE_SIZE, bold=True))
        self._title.grid(row=0, column=0, pady=(theme.PAD_L, theme.PAD_S))

        self._instruction = ctk.CTkLabel(
            self, text="", font=theme.font(), wraplength=380, justify="center"
        )
        self._instruction.grid(row=1, column=0, padx=theme.PAD_L, pady=theme.PAD_S)

        self._progress = ctk.CTkProgressBar(self)
        self._progress.set(0)
        self._progress.grid(row=2, column=0, sticky="ew", padx=theme.PAD_L, pady=theme.PAD_M)

        self._action = ctk.CTkButton(
            self, text="Start", command=self._start_step, fg_color=theme.ACCENT
        )
        self._action.grid(row=3, column=0, pady=theme.PAD_M)

        self.protocol("WM_DELETE_WINDOW", self._close)
        self._show_step()

    # -- step flow ---------------------------------------------------------
    def _show_step(self) -> None:
        gesture = _STEPS[self._step]
        self._title.configure(text=f"Step {self._step + 1} of {len(_STEPS)}")
        self._instruction.configure(
            text=f"Hold a clear “{gesture.label}” gesture, then press Start and keep holding."
        )
        self._progress.set(0)
        self._action.configure(text="Start", state="normal", command=self._start_step)

    def _start_step(self) -> None:
        self._collecting = True
        self._collected = 0
        self._action.configure(state="disabled", text="Collecting…")
        self._poll()

    def _poll(self) -> None:
        if not self._collecting:
            return
        target = _STEPS[self._step]
        result = self._engine.latest_result
        if result.gesture is target and result.confidence > 0.0:
            self._service.add_sample(result)
            self._collected += 1
            self._progress.set(self._collected / _SAMPLES_PER_STEP)

        if self._collected >= _SAMPLES_PER_STEP:
            self._finish_step()
        else:
            self._poll_id = self.after(_POLL_MS, self._poll)

    def _finish_step(self) -> None:
        self._collecting = False
        if self._step + 1 < len(_STEPS):
            self._step += 1
            self._action.configure(state="normal", text="Next", command=self._advance)
            self._instruction.configure(text="Great! Press Next for the following gesture.")
        else:
            self._action.configure(state="normal", text="Finish", command=self._finish)
            self._instruction.configure(text="All gestures captured. Press Finish to save.")

    def _advance(self) -> None:
        self._show_step()

    def _finish(self) -> None:
        profile = self._service.build_profile()
        try:
            self._service.save(profile)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to save calibration")
            self._instruction.configure(text=f"Could not save calibration: {exc}")
            return
        logger.info("Calibration complete: %s", profile.to_dict())
        self._on_saved()
        self._close()

    def _close(self) -> None:
        self._collecting = False
        if self._poll_id is not None:
            self.after_cancel(self._poll_id)
        self.destroy()
