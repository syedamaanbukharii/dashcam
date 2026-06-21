"""Small reusable widgets for the main window.

These are deliberately dumb views: they expose ``set_*``/``show``/``hide``
methods the controller calls in response to engine events, and hold no
application logic of their own.
"""

from __future__ import annotations

import customtkinter as ctk

from . import theme


class StatusBar(ctk.CTkFrame):
    """Bottom bar showing a status message, FPS and the detection-lock state."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master, fg_color=theme.SURFACE_MUTED, height=32)
        self.grid_columnconfigure(0, weight=1)

        self._status = ctk.CTkLabel(self, text="Ready", font=theme.font(), anchor="w")
        self._status.grid(row=0, column=0, sticky="ew", padx=theme.PAD_M)

        self._lock = ctk.CTkLabel(self, text="", font=theme.font(), text_color=theme.WARNING)
        self._lock.grid(row=0, column=1, padx=theme.PAD_M)

        self._fps = ctk.CTkLabel(
            self, text="-- fps", font=theme.font(), text_color=theme.TEXT_MUTED
        )
        self._fps.grid(row=0, column=2, sticky="e", padx=theme.PAD_M)

    def set_status(self, text: str, level: str = "info") -> None:
        self._status.configure(text=text, text_color=theme.level_color(level))

    def set_fps(self, fps: float) -> None:
        self._fps.configure(text=f"{fps:4.1f} fps")

    def set_locked(self, locked: bool) -> None:
        self._lock.configure(text="🔒 detection locked" if locked else "")


class GuidanceLabel(ctk.CTkLabel):
    """Overlay line at the top of the preview giving framing guidance."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(
            master,
            text="",
            font=theme.font(theme.BODY_SIZE + 1, bold=True),
            fg_color=theme.SURFACE_MUTED,
            corner_radius=8,
            text_color=theme.TEXT_PRIMARY,
        )

    def set_guidance(self, text: str, ready: bool) -> None:
        self.configure(text=text, text_color=theme.SUCCESS if ready else theme.TEXT_PRIMARY)


class CountdownOverlay(ctk.CTkLabel):
    """Large translucent countdown number centred over the preview."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(
            master,
            text="",
            font=theme.font(theme.COUNTDOWN_SIZE, bold=True),
            text_color=theme.TEXT_PRIMARY,
            fg_color="transparent",
        )

    def show(self, value: int) -> None:
        self.configure(text="📸" if value <= 0 else str(value))
        self.place(relx=0.5, rely=0.5, anchor="center")

    def hide(self) -> None:
        self.place_forget()


class Toast(ctk.CTkLabel):
    """Transient message that auto-dismisses after a short delay."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(
            master,
            text="",
            font=theme.font(bold=True),
            fg_color=theme.SUCCESS,
            corner_radius=8,
            text_color="#062B12",
        )
        self._after_id: str | None = None

    def flash(self, text: str, *, level: str = "info", duration_ms: int = 1800) -> None:
        color = {"info": theme.SUCCESS, "warning": theme.WARNING, "error": theme.ERROR}.get(
            level, theme.SUCCESS
        )
        self.configure(text=text, fg_color=color)
        self.place(relx=0.5, rely=0.9, anchor="center")
        if self._after_id is not None:
            self.after_cancel(self._after_id)
        self._after_id = self.after(duration_ms, self.place_forget)
