"""The settings window.

Presents the full :class:`~gesturecam.config.schema.AppConfig` across a set of
tabs. Each control registers a small getter; on save we assemble a config dict,
rebuild and validate an :class:`AppConfig`, persist it via the
:class:`~gesturecam.config.manager.ConfigManager` and notify the caller.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ..config.manager import ConfigManager
from ..config.schema import AppConfig
from ..errors import InvalidConfigurationError
from ..logging_setup import get_logger
from . import theme

logger = get_logger(__name__)


class SettingsWindow(ctk.CTkToplevel):  # pragma: no cover - requires a display
    """Modal-ish settings editor bound to an :class:`AppConfig`."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        config: AppConfig,
        manager: ConfigManager,
        *,
        on_saved: Callable[[AppConfig], None],
    ) -> None:
        super().__init__(master)
        self._config = config
        self._manager = manager
        self._on_saved = on_saved
        self._getters: dict[str, Callable[[], Any]] = {}

        self.title("Settings")
        self.geometry("560x620")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        tabs = ctk.CTkTabview(self)
        tabs.grid(row=0, column=0, sticky="nsew", padx=theme.PAD_M, pady=theme.PAD_M)
        for name in ("Camera", "Gestures", "Capture", "Face", "Quality", "Audio", "Storage"):
            tabs.add(name)

        self._build_camera(tabs.tab("Camera"))
        self._build_gestures(tabs.tab("Gestures"))
        self._build_capture(tabs.tab("Capture"))
        self._build_face(tabs.tab("Face"))
        self._build_quality(tabs.tab("Quality"))
        self._build_audio(tabs.tab("Audio"))
        self._build_storage(tabs.tab("Storage"))

        self._error = ctk.CTkLabel(self, text="", text_color=theme.ERROR, font=theme.font())
        self._error.grid(row=1, column=0, sticky="ew", padx=theme.PAD_M)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=2, column=0, sticky="e", padx=theme.PAD_M, pady=theme.PAD_M)
        ctk.CTkButton(
            buttons, text="Cancel", command=self.destroy, fg_color=theme.SURFACE_MUTED
        ).grid(row=0, column=0, padx=theme.PAD_S)
        ctk.CTkButton(buttons, text="Save", command=self._save, fg_color=theme.ACCENT).grid(
            row=0, column=1, padx=theme.PAD_S
        )

    # -- field builders ----------------------------------------------------
    def _switch(self, parent: ctk.CTkBaseClass, key: str, label: str, value: bool) -> None:
        var = ctk.BooleanVar(value=value)
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=theme.PAD_S)
        ctk.CTkLabel(row, text=label, font=theme.font(), width=220, anchor="w").pack(side="left")
        ctk.CTkSwitch(row, text="", variable=var).pack(side="right")
        self._getters[key] = var.get

    def _slider(
        self,
        parent: ctk.CTkBaseClass,
        key: str,
        label: str,
        value: float,
        lo: float,
        hi: float,
        *,
        integer: bool = False,
    ) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=theme.PAD_S)
        readout = ctk.CTkLabel(row, text=_fmt(value, integer), font=theme.font(), width=48)
        ctk.CTkLabel(row, text=label, font=theme.font(), width=180, anchor="w").pack(side="left")
        readout.pack(side="right")
        slider = ctk.CTkSlider(row, from_=lo, to=hi)
        slider.set(value)
        slider.configure(command=lambda v: readout.configure(text=_fmt(v, integer)))
        slider.pack(side="right", fill="x", expand=True, padx=theme.PAD_M)
        self._getters[key] = (lambda: int(slider.get())) if integer else slider.get

    def _entry(self, parent: ctk.CTkBaseClass, key: str, label: str, value: str) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=theme.PAD_S)
        ctk.CTkLabel(row, text=label, font=theme.font(), width=180, anchor="w").pack(side="left")
        entry = ctk.CTkEntry(row)
        entry.insert(0, value)
        entry.pack(side="right", fill="x", expand=True, padx=theme.PAD_M)
        self._getters[key] = entry.get

    def _choice(
        self, parent: ctk.CTkBaseClass, key: str, label: str, value: str, options: list[str]
    ) -> None:
        var = ctk.StringVar(value=value)
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=theme.PAD_S)
        ctk.CTkLabel(row, text=label, font=theme.font(), width=180, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(row, values=options, variable=var).pack(side="right", padx=theme.PAD_M)
        self._getters[key] = var.get

    # -- tabs --------------------------------------------------------------
    def _build_camera(self, tab: ctk.CTkBaseClass) -> None:
        cam = self._config.camera
        self._slider(tab, "camera.index", "Camera index", cam.index, 0, 8, integer=True)
        self._slider(tab, "camera.width", "Width", cam.width, 320, 3840, integer=True)
        self._slider(tab, "camera.height", "Height", cam.height, 240, 2160, integer=True)
        self._slider(tab, "camera.fps", "Target FPS", cam.fps, 5, 60, integer=True)
        self._switch(tab, "camera.mirror", "Mirror preview", cam.mirror)
        self._choice(tab, "theme", "Appearance", self._config.theme, ["system", "light", "dark"])

    def _build_gestures(self, tab: ctk.CTkBaseClass) -> None:
        rec = self._config.recognition
        self._slider(tab, "recognition.max_hands", "Max hands", rec.max_hands, 1, 2, integer=True)
        self._slider(
            tab,
            "recognition.min_detection_confidence",
            "Detection conf",
            rec.min_detection_confidence,
            0.1,
            0.9,
        )
        self._slider(
            tab,
            "recognition.min_tracking_confidence",
            "Tracking conf",
            rec.min_tracking_confidence,
            0.1,
            0.9,
        )
        self._slider(
            tab, "recognition.window_size", "Smoothing window", rec.window_size, 3, 20, integer=True
        )
        self._slider(
            tab,
            "recognition.min_consistent_frames",
            "Consistent frames",
            rec.min_consistent_frames,
            1,
            20,
            integer=True,
        )
        self._slider(
            tab, "recognition.min_confidence", "Trigger confidence", rec.min_confidence, 0.3, 0.95
        )
        self._slider(
            tab, "recognition.cooldown_seconds", "Cooldown (s)", rec.cooldown_seconds, 0.0, 5.0
        )

    def _build_capture(self, tab: ctk.CTkBaseClass) -> None:
        self._switch(
            tab, "countdown.enabled", "Countdown before photo", self._config.countdown.enabled
        )
        self._slider(
            tab,
            "countdown.seconds",
            "Countdown seconds",
            self._config.countdown.seconds,
            0,
            10,
            integer=True,
        )
        self._slider(
            tab, "burst.count", "Burst count", self._config.burst.count, 1, 15, integer=True
        )
        self._slider(
            tab,
            "burst.delay_ms",
            "Burst delay (ms)",
            self._config.burst.delay_ms,
            50,
            1000,
            integer=True,
        )
        self._switch(
            tab,
            "best_shot.keep_best_only",
            "Keep only the best burst shot",
            self._config.best_shot.keep_best_only,
        )

    def _build_face(self, tab: ctk.CTkBaseClass) -> None:
        face = self._config.face
        self._switch(tab, "face.require_face", "Require a face", face.require_face)
        self._switch(
            tab, "face.allow_multiple_faces", "Allow multiple faces", face.allow_multiple_faces
        )
        self._switch(tab, "face.require_smile", "Require a smile", face.require_smile)
        self._switch(tab, "face.validate_eyes", "Require open eyes", face.validate_eyes)
        self._slider(tab, "face.ear_threshold", "Eye-open threshold", face.ear_threshold, 0.05, 0.4)
        self._slider(tab, "face.smile_threshold", "Smile threshold", face.smile_threshold, 0.2, 0.9)
        self._slider(
            tab, "face.center_tolerance", "Centre tolerance", face.center_tolerance, 0.05, 0.5
        )

    def _build_quality(self, tab: ctk.CTkBaseClass) -> None:
        self._switch(
            tab, "quality.reject_blurry", "Reject blurry photos", self._config.quality.reject_blurry
        )
        self._slider(
            tab,
            "quality.blur_threshold",
            "Blur threshold",
            self._config.quality.blur_threshold,
            10,
            400,
        )
        enh = self._config.enhancement
        self._switch(tab, "enhancement.enabled", "Auto-enhance photos", enh.enabled)
        self._slider(tab, "enhancement.contrast", "Contrast", enh.contrast, 0.8, 1.4)
        self._slider(tab, "enhancement.brightness", "Brightness", enh.brightness, 0.8, 1.4)
        self._slider(tab, "enhancement.sharpen", "Sharpen", enh.sharpen, 0.8, 1.4)
        self._switch(
            tab,
            "background.enabled",
            "Remove background (needs rembg)",
            self._config.background.enabled,
        )

    def _build_audio(self, tab: ctk.CTkBaseClass) -> None:
        audio = self._config.audio
        self._switch(tab, "audio.voice_enabled", "Voice feedback", audio.voice_enabled)
        self._slider(tab, "audio.rate", "Speech rate", audio.rate, 80, 300, integer=True)
        self._slider(tab, "audio.volume", "Volume", audio.volume, 0.0, 1.0)

    def _build_storage(self, tab: ctk.CTkBaseClass) -> None:
        storage = self._config.storage
        self._entry(tab, "storage.save_folder", "Save folder", storage.save_folder)
        self._choice(
            tab, "storage.image_format", "Image format", storage.image_format, ["jpg", "png"]
        )
        self._slider(
            tab, "storage.jpeg_quality", "JPEG quality", storage.jpeg_quality, 50, 100, integer=True
        )

    # -- save --------------------------------------------------------------
    def _save(self) -> None:
        data = self._config.to_dict()
        for key, getter in self._getters.items():
            _assign(data, key, getter())
        try:
            config = AppConfig.from_dict(data)
            config.validate()
            self._manager.save(config)
        except InvalidConfigurationError as exc:
            self._error.configure(text=str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - surface any save failure
            logger.exception("Failed to save settings")
            self._error.configure(text=f"Could not save: {exc}")
            return
        self._on_saved(config)
        self.destroy()


def _assign(data: dict[str, Any], dotted_key: str, value: Any) -> None:
    head, _, tail = dotted_key.partition(".")
    if tail:
        node = data.setdefault(head, {})
        if isinstance(node, dict):
            _assign(node, tail, value)
    else:
        data[head] = value


def _fmt(value: float, integer: bool) -> str:
    return str(int(round(value))) if integer else f"{value:.2f}"
