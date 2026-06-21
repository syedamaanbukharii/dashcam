"""The main application window.

:class:`GestureCamApp` is the controller: it builds the engine and its
dependencies via the :class:`~gesturecam.services.factory.DependencyFactory`,
renders the live preview, and translates engine events drained from the
:class:`~gesturecam.services.events.EventBus` into widget updates. The engine
runs on its own thread; this class only ever touches widgets from Tk's loop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk
import numpy as np
from numpy.typing import NDArray
from PIL import Image

from .. import APP_NAME
from ..config.manager import ConfigManager
from ..config.schema import AppConfig
from ..errors import CameraError, DependencyError, GestureCamError, ModelError
from ..face.types import GUIDANCE
from ..gestures.types import Action
from ..logging_setup import get_logger
from ..services.capture_service import CaptureService
from ..services.engine import GestureEngine
from ..services.events import (
    BurstProgress,
    CaptureSaved,
    CountdownTick,
    DetectionLockChanged,
    EngineStopped,
    EventBus,
    FrameReady,
    GestureDetected,
    PositioningUpdate,
    RecordingStateChanged,
    StatusMessage,
)
from ..services.factory import DependencyFactory
from ..storage.database import CaptureDatabase
from . import theme
from .widgets import CountdownOverlay, GuidanceLabel, StatusBar, Toast

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..gallery.service import GalleryService

logger = get_logger(__name__)

_POLL_MS = 15


class GestureCamApp(ctk.CTk):  # pragma: no cover - requires a display
    """Main window wiring widgets to the gesture engine."""

    def __init__(self, config: AppConfig, config_manager: ConfigManager) -> None:
        super().__init__()
        self._config = config
        self._config_manager = config_manager
        self._bus = EventBus()
        self._engine: GestureEngine | None = None
        self._database: CaptureDatabase | None = None
        self._gallery: GalleryService | None = None
        self._preview_image: ctk.CTkImage | None = None

        theme.apply_appearance(config.theme)
        self.title(APP_NAME)
        self.geometry("1024x720")
        self.minsize(800, 560)

        self._build_layout()
        self._start_engine()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(_POLL_MS, self._poll_events)

    # -- layout ------------------------------------------------------------
    def _build_layout(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        toolbar = ctk.CTkFrame(self, fg_color=theme.SURFACE)
        toolbar.grid(row=0, column=0, sticky="ew")
        self._build_toolbar(toolbar)

        self._preview = ctk.CTkLabel(self, text="Starting camera…", fg_color="#000000")
        self._preview.grid(row=1, column=0, sticky="nsew")

        self._guidance = GuidanceLabel(self._preview)
        self._guidance.place(relx=0.5, rely=0.06, anchor="center")
        self._countdown = CountdownOverlay(self._preview)
        self._toast = Toast(self._preview)

        self._status = StatusBar(self)
        self._status.grid(row=2, column=0, sticky="ew")

    def _build_toolbar(self, toolbar: ctk.CTkFrame) -> None:
        def button(text: str, command: object, col: int, color: str = theme.ACCENT) -> None:
            ctk.CTkButton(
                toolbar,
                text=text,
                command=command,  # type: ignore[arg-type]
                fg_color=color,
                hover_color=theme.ACCENT_HOVER,
                font=theme.font(bold=True),
                width=110,
            ).grid(row=0, column=col, padx=theme.PAD_S, pady=theme.PAD_M)

        button("📷 Photo", lambda: self._request(Action.PHOTO), 0)
        button("⚡ Burst", lambda: self._request(Action.BURST), 1)
        self._record_button = ctk.CTkButton(
            toolbar,
            text="⏺ Record",
            command=lambda: self._request(Action.VIDEO_TOGGLE),
            fg_color=theme.ERROR,
            hover_color="#B91C1C",
            font=theme.font(bold=True),
            width=110,
        )
        self._record_button.grid(row=0, column=2, padx=theme.PAD_S, pady=theme.PAD_M)
        button("🔒 Lock", lambda: self._request(Action.LOCK_DETECTION), 3, theme.SURFACE_MUTED)
        button("🖼 Gallery", self._open_gallery, 4, theme.SURFACE_MUTED)
        button("🎯 Calibrate", self._open_calibration, 5, theme.SURFACE_MUTED)
        button("⚙ Settings", self._open_settings, 6, theme.SURFACE_MUTED)

    # -- engine ------------------------------------------------------------
    def _start_engine(self) -> None:
        # The database and gallery are light and always available, so the user
        # can browse captures even if the camera or models are unavailable.
        factory = DependencyFactory(self._config)
        from ..gallery.service import GalleryService

        self._database = factory.build_database()
        self._gallery = GalleryService(self._database)

        try:
            voice = factory.build_voice()
            capture = CaptureService(self._config, self._database, voice)
            camera = factory.build_camera()
            hand_detector = factory.build_hand_detector()
            face_detector = factory.build_face_detector()
            recorder = factory.build_recorder()
        except (DependencyError, ModelError, CameraError) as exc:
            logger.exception("Engine dependencies unavailable")
            self._status.set_status(str(exc), level="error")
            self._preview.configure(text="Camera/model unavailable\nSee status bar")
            return
        except GestureCamError as exc:  # any other domain error
            logger.exception("Failed to initialise engine")
            self._status.set_status(str(exc), level="error")
            return

        # Apply any saved per-user calibration to the classifier.
        from ..services.calibration import CalibrationService

        classifier_params = CalibrationService.load().to_params()

        self._engine = GestureEngine(
            self._config,
            camera=camera,
            hand_detector=hand_detector,
            face_detector=face_detector,
            capture_service=capture,
            recorder=recorder,
            voice=voice,
            bus=self._bus,
            classifier_params=classifier_params,
        )
        self._engine.start()
        self._status.set_status("Show a gesture to begin", level="info")

    def _request(self, action: Action) -> None:
        if self._engine is not None:
            self._engine.request_action(action)
        else:
            self._status.set_status("Engine is not running", level="warning")

    # -- event loop --------------------------------------------------------
    def _poll_events(self) -> None:
        for event in self._bus.drain():
            self._handle_event(event)
        self.after(_POLL_MS, self._poll_events)

    def _handle_event(self, event: object) -> None:
        if isinstance(event, FrameReady):
            self._render_frame(event.image, event.fps)
        elif isinstance(event, PositioningUpdate):
            positioning = event.positioning
            self._guidance.set_guidance(positioning.guidance, positioning.ready)
        elif isinstance(event, CountdownTick):
            if event.value <= 0:
                self._countdown.show(0)
                self.after(400, self._countdown.hide)
            else:
                self._countdown.show(event.value)
        elif isinstance(event, GestureDetected):
            self._status.set_status(f"{event.gesture.label} → {event.action.label}", level="info")
        elif isinstance(event, CaptureSaved):
            self._toast.flash("Saved ✓", level="info")
            self._status.set_status(f"Saved {event.record.filename}", level="info")
        elif isinstance(event, BurstProgress):
            self._status.set_status(f"Burst {event.captured}/{event.total}", level="info")
        elif isinstance(event, RecordingStateChanged):
            self._on_recording_changed(event.recording)
        elif isinstance(event, DetectionLockChanged):
            self._status.set_locked(event.locked)
        elif isinstance(event, StatusMessage):
            self._status.set_status(event.text, level=event.level)
            if event.level in {"warning", "error"}:
                self._toast.flash(event.text, level=event.level)
        elif isinstance(event, EngineStopped):
            self._status.set_status("Engine stopped", level="warning")

    def _render_frame(self, image_bgr: NDArray[np.uint8], fps: float) -> None:
        rgb = np.ascontiguousarray(image_bgr[:, :, ::-1])
        pil = Image.fromarray(rgb)
        size = self._fit_size(pil.width, pil.height)
        self._preview_image = ctk.CTkImage(light_image=pil, dark_image=pil, size=size)
        self._preview.configure(image=self._preview_image, text="")
        self._status.set_fps(fps)

    def _fit_size(self, width: int, height: int) -> tuple[int, int]:
        avail_w = max(320, self._preview.winfo_width())
        avail_h = max(240, self._preview.winfo_height())
        scale = min(avail_w / width, avail_h / height)
        return (int(width * scale), int(height * scale))

    def _on_recording_changed(self, recording: bool) -> None:
        self._record_button.configure(text="⏹ Stop" if recording else "⏺ Record")
        self._status.set_status("Recording…" if recording else "Recording saved", level="info")

    # -- secondary windows -------------------------------------------------
    def _open_settings(self) -> None:
        from .settings_window import SettingsWindow

        SettingsWindow(self, self._config, self._config_manager, on_saved=self._on_config_saved)

    def _open_gallery(self) -> None:
        if self._gallery is None:
            return
        from .gallery_window import GalleryWindow

        GalleryWindow(self, self._gallery)

    def _open_calibration(self) -> None:
        if self._engine is None:
            self._status.set_status("Calibration needs a running camera", level="warning")
            return
        from .calibration_window import CalibrationWindow

        CalibrationWindow(self, self._engine, on_saved=self._on_calibration_saved)

    def _on_config_saved(self, config: AppConfig) -> None:
        self._config = config
        theme.apply_appearance(config.theme)
        self._status.set_status("Settings saved — restart to apply camera changes", level="info")

    def _on_calibration_saved(self) -> None:
        self._status.set_status("Calibration saved — restart to apply", level="info")

    # -- shutdown ----------------------------------------------------------
    def _on_close(self) -> None:
        logger.info("Shutting down UI")
        if self._engine is not None:
            self._engine.stop()
        if self._database is not None:
            self._database.close()
        self.destroy()

    # GUIDANCE is imported to ensure the mapping is bundled even if unused here.
    _ = GUIDANCE
