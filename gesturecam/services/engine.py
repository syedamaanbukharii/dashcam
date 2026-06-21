"""The processing engine: the heart that ties every subsystem together.

A single daemon thread runs the loop: grab the latest frame, detect faces (for
framing guidance and capture quality), detect and classify hands, feed the
result through the temporal stabiliser, and dispatch the mapped action. Photo
and burst captures run through small time-based state machines so the loop never
blocks on a countdown. All output to the UI goes through the
:class:`~gesturecam.services.events.EventBus`; the engine never touches widgets.
"""

from __future__ import annotations

import queue
import threading
import time

from ..audio.tts import Voice
from ..config.schema import AppConfig
from ..face.analysis import PositioningParams, analyze_positioning
from ..face.detector import FaceDetection, FaceDetector
from ..gestures.classifier import ClassifierParams
from ..gestures.recognizer import HandDetector, recognise_gestures
from ..gestures.stabilizer import GestureStabilizer, StabilizerParams
from ..gestures.types import Action, FingerStates, Gesture, GestureResult
from ..logging_setup import get_logger
from .capture_service import CaptureService
from .events import (
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

logger = get_logger(__name__)

_COUNTDOWN_WORDS = {3: "Three", 2: "Two", 1: "One"}


def _none_result() -> GestureResult:
    return GestureResult(
        gesture=Gesture.NONE,
        confidence=0.0,
        fingers=FingerStates(False, False, False, False, False),
    )


class GestureEngine:
    """Owns the capture/detect/dispatch loop on a background thread."""

    def __init__(
        self,
        config: AppConfig,
        *,
        camera: object,
        hand_detector: HandDetector,
        face_detector: FaceDetector,
        capture_service: CaptureService,
        recorder: object,
        voice: Voice,
        bus: EventBus,
        classifier_params: ClassifierParams | None = None,
    ) -> None:
        self._config = config
        self._camera = camera
        self._hand_detector = hand_detector
        self._face_detector = face_detector
        self._capture = capture_service
        self._recorder = recorder
        self._voice = voice
        self._bus = bus
        self._classifier_params = classifier_params or ClassifierParams()

        self._stabilizer = GestureStabilizer(
            StabilizerParams(
                window_size=config.recognition.window_size,
                min_consistent_frames=config.recognition.min_consistent_frames,
                min_confidence=config.recognition.min_confidence,
                cooldown_seconds=config.recognition.cooldown_seconds,
            )
        )
        self._positioning_params = PositioningParams(
            require_face=config.face.require_face,
            allow_multiple_faces=config.face.allow_multiple_faces,
            min_face_area_ratio=config.face.min_face_area_ratio,
            max_face_area_ratio=config.face.max_face_area_ratio,
            center_tolerance=config.face.center_tolerance,
        )

        self._thread: threading.Thread | None = None
        self._running = threading.Event()
        self._locked = False
        self._last_index = -1
        self._latest_faces: list[FaceDetection] = []
        self._latest_result: GestureResult = _none_result()
        self._result_lock = threading.Lock()
        self._commands: queue.Queue[Action] = queue.Queue()

        # countdown / burst state
        self._countdown_value = 0
        self._countdown_next = 0.0
        self._pending: str | None = None  # "single" | "burst"
        self._burst_remaining = 0
        self._burst_next = 0.0
        self._burst_frames: list[tuple[object, list[FaceDetection]]] = []

        # fps tracking
        self._fps = 0.0
        self._last_frame_time = 0.0

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        if self._running.is_set():
            return
        self._running.set()
        self._thread = threading.Thread(target=self._loop, name="gesture-engine", daemon=True)
        self._thread.start()
        logger.info("Gesture engine started")

    def stop(self) -> None:
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        if getattr(self._recorder, "is_recording", False):
            self._recorder.stop()  # type: ignore[attr-defined]
        logger.info("Gesture engine stopped")

    @property
    def is_running(self) -> bool:
        return self._running.is_set()

    @property
    def detection_locked(self) -> bool:
        return self._locked

    @property
    def latest_result(self) -> GestureResult:
        """The most recent raw (pre-stabilisation) classification result."""
        with self._result_lock:
            return self._latest_result

    def request_action(self, action: Action) -> None:
        """Queue an action from the UI; processed on the engine thread."""
        self._commands.put(action)

    # -- main loop ---------------------------------------------------------
    def _loop(self) -> None:  # pragma: no cover - requires hardware + heavy deps
        try:
            self._camera.open()  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            logger.exception("Camera failed to open")
            self._bus.publish(StatusMessage(text=str(exc), level="error"))
            self._bus.publish(EngineStopped(reason="camera-error"))
            self._running.clear()
            return

        while self._running.is_set():
            frame = self._camera.read()  # type: ignore[attr-defined]
            if frame is None or frame.index == self._last_index:
                time.sleep(0.005)
                continue
            self._last_index = frame.index
            now = time.monotonic()

            self._drain_commands(frame, now)
            self._process_faces(frame)
            if not self._locked and self._pending is None and self._burst_remaining == 0:
                self._process_gestures(frame, now)
            self._tick_capture(frame, now)

            if getattr(self._recorder, "is_recording", False):
                self._recorder.write(frame.image)  # type: ignore[attr-defined]

            self._update_fps(now)
            self._bus.publish(FrameReady(image=frame.image, fps=self._fps))

        self._camera.close()  # type: ignore[attr-defined]
        self._bus.publish(EngineStopped(reason="stopped"))

    # -- per-frame work ----------------------------------------------------
    def _drain_commands(self, frame: object, now: float) -> None:  # pragma: no cover
        while True:
            try:
                action = self._commands.get_nowait()
            except queue.Empty:
                break
            self._dispatch_action(action, frame, now)

    def _process_faces(self, frame: object) -> None:  # pragma: no cover - heavy deps
        faces = self._face_detector.detect(frame.image, frame.timestamp_ms)  # type: ignore[attr-defined]
        self._latest_faces = faces
        positioning = analyze_positioning(
            [f.box for f in faces],
            frame.width,  # type: ignore[attr-defined]
            frame.height,  # type: ignore[attr-defined]
            self._positioning_params,
        )
        self._bus.publish(PositioningUpdate(positioning=positioning))

    def _process_gestures(self, frame: object, now: float) -> None:  # pragma: no cover
        hands = self._hand_detector.detect(frame.image, frame.timestamp_ms)  # type: ignore[attr-defined]
        results = recognise_gestures(hands, self._classifier_params)
        result = max(results, key=lambda r: r.confidence) if results else _none_result()
        with self._result_lock:
            self._latest_result = result
        triggered = self._stabilizer.update(result, now)
        if triggered is not None and triggered is not Gesture.NONE:
            self._dispatch(triggered, frame, now)

    def _dispatch(self, gesture: Gesture, frame: object, now: float) -> None:  # pragma: no cover
        action = self._config.gestures.action_for(gesture)
        logger.info("Gesture %s -> action %s", gesture.value, action.value)
        self._bus.publish(GestureDetected(gesture=gesture, action=action))
        self._dispatch_action(action, frame, now)

    def _dispatch_action(
        self, action: Action, frame: object, now: float
    ) -> None:  # pragma: no cover
        if action is Action.PHOTO:
            self._begin_capture("single", now)
        elif action is Action.BURST:
            self._begin_capture("burst", now)
        elif action is Action.VIDEO_TOGGLE:
            self._toggle_recording(frame)
        elif action is Action.LOCK_DETECTION:
            self._toggle_lock()
        elif action is Action.EXIT:
            self._bus.publish(StatusMessage(text="Exiting", level="info"))
            self._running.clear()

    # -- countdown / burst state machine -----------------------------------
    def _begin_capture(self, kind: str, now: float) -> None:  # pragma: no cover
        countdown = self._config.countdown
        if countdown.enabled and countdown.seconds > 0:
            self._pending = kind
            self._countdown_value = countdown.seconds
            self._countdown_next = now + 1.0
            self._announce_countdown(self._countdown_value)
            self._bus.publish(CountdownTick(value=self._countdown_value))
        elif kind == "single":
            self._do_single_capture()
        else:
            self._start_burst(now)

    def _tick_capture(self, frame: object, now: float) -> None:  # pragma: no cover
        if self._pending is not None and now >= self._countdown_next:
            self._countdown_value -= 1
            if self._countdown_value > 0:
                self._announce_countdown(self._countdown_value)
                self._bus.publish(CountdownTick(value=self._countdown_value))
                self._countdown_next = now + 1.0
            else:
                self._bus.publish(CountdownTick(value=0))
                self._voice.say("Smile")
                pending, self._pending = self._pending, None
                if pending == "single":
                    self._do_single_capture()
                else:
                    self._start_burst(now)

        if self._burst_remaining > 0 and now >= self._burst_next:
            self._capture_burst_frame(frame, now)

    def _start_burst(self, now: float) -> None:  # pragma: no cover
        self._burst_remaining = self._config.burst.count
        self._burst_frames = []
        self._burst_next = now

    def _capture_burst_frame(self, frame: object, now: float) -> None:  # pragma: no cover
        self._burst_frames.append((frame.image.copy(), list(self._latest_faces)))  # type: ignore[attr-defined]
        self._burst_remaining -= 1
        captured = self._config.burst.count - self._burst_remaining
        self._bus.publish(BurstProgress(captured=captured, total=self._config.burst.count))
        self._burst_next = now + self._config.burst.delay_ms / 1000.0
        if self._burst_remaining == 0:
            outcome = self._capture.process_burst(self._burst_frames)
            self._burst_frames = []
            if outcome.best is not None:
                self._bus.publish(CaptureSaved(record=outcome.best))
            else:
                self._bus.publish(StatusMessage(text="No good shot in burst", level="warning"))

    def _do_single_capture(self) -> None:  # pragma: no cover
        frame = self._camera.read()  # type: ignore[attr-defined]
        if frame is None:
            return
        outcome = self._capture.process_single(frame.image, self._latest_faces)
        if outcome.saved and outcome.record is not None:
            self._bus.publish(CaptureSaved(record=outcome.record))
        elif outcome.rejected_reason:
            self._voice.say(outcome.rejected_reason)
            self._bus.publish(StatusMessage(text=outcome.rejected_reason, level="warning"))

    # -- toggles -----------------------------------------------------------
    def _toggle_recording(self, frame: object) -> None:  # pragma: no cover
        if getattr(self._recorder, "is_recording", False):
            path = self._recorder.stop()  # type: ignore[attr-defined]
            if path is not None:
                self._capture.register_video(
                    path, width=frame.width, height=frame.height  # type: ignore[attr-defined]
                )
            self._voice.say("Recording stopped")
            self._bus.publish(RecordingStateChanged(recording=False, path=path))
        else:
            path = self._recorder.start((frame.width, frame.height))  # type: ignore[attr-defined]
            self._voice.say("Recording")
            self._bus.publish(RecordingStateChanged(recording=True, path=path))

    def _toggle_lock(self) -> None:  # pragma: no cover
        self._locked = not self._locked
        self._stabilizer.reset()
        state = "locked" if self._locked else "unlocked"
        self._voice.say(f"Detection {state}")
        self._bus.publish(DetectionLockChanged(locked=self._locked))

    # -- helpers -----------------------------------------------------------
    def _announce_countdown(self, value: int) -> None:  # pragma: no cover
        self._voice.say(_COUNTDOWN_WORDS.get(value, str(value)))

    def _update_fps(self, now: float) -> None:  # pragma: no cover
        if self._last_frame_time:
            delta = now - self._last_frame_time
            if delta > 0:
                instantaneous = 1.0 / delta
                self._fps = (
                    instantaneous if self._fps == 0 else 0.9 * self._fps + 0.1 * instantaneous
                )
        self._last_frame_time = now
