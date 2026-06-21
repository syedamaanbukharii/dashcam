"""Strongly-typed configuration schema.

Configuration is modelled as a tree of frozen-ish dataclasses rather than a
loose dictionary, so every consumer gets type checking and autocompletion and
invalid values are rejected centrally by :meth:`AppConfig.validate`.

The tree round-trips to JSON: :meth:`AppConfig.to_dict` produces a JSON-safe
structure (enums become their string values) and :meth:`AppConfig.from_dict`
rebuilds the typed tree, tolerating missing keys by falling back to defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from typing import Any

from .. import paths
from ..errors import InvalidConfigurationError
from ..gestures.types import Action, Gesture


def _to_jsonable(obj: Any) -> Any:
    """Recursively convert dataclasses/enums into JSON-serialisable values."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _to_jsonable(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {_to_jsonable(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(item) for item in obj]
    return obj


def _get(data: dict[str, Any], key: str, default: Any) -> Any:
    value = data.get(key, default)
    return default if value is None else value


@dataclass
class CameraConfig:
    index: int = 0
    width: int = 1280
    height: int = 720
    fps: int = 30
    mirror: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CameraConfig:
        return cls(
            index=int(_get(data, "index", 0)),
            width=int(_get(data, "width", 1280)),
            height=int(_get(data, "height", 720)),
            fps=int(_get(data, "fps", 30)),
            mirror=bool(_get(data, "mirror", True)),
        )


@dataclass
class RecognitionConfig:
    max_hands: int = 2
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    window_size: int = 8
    min_consistent_frames: int = 5
    min_confidence: float = 0.6
    cooldown_seconds: float = 1.5

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecognitionConfig:
        return cls(
            max_hands=int(_get(data, "max_hands", 2)),
            min_detection_confidence=float(_get(data, "min_detection_confidence", 0.5)),
            min_tracking_confidence=float(_get(data, "min_tracking_confidence", 0.5)),
            window_size=int(_get(data, "window_size", 8)),
            min_consistent_frames=int(_get(data, "min_consistent_frames", 5)),
            min_confidence=float(_get(data, "min_confidence", 0.6)),
            cooldown_seconds=float(_get(data, "cooldown_seconds", 1.5)),
        )


def _default_mapping() -> dict[Gesture, Action]:
    return {
        Gesture.PEACE: Action.PHOTO,
        Gesture.THUMBS_UP: Action.BURST,
        Gesture.PINCH: Action.VIDEO_TOGGLE,
        Gesture.FIST: Action.LOCK_DETECTION,
        Gesture.THUMBS_DOWN: Action.EXIT,
        Gesture.OPEN_PALM: Action.NONE,
    }


@dataclass
class GestureMappingConfig:
    mapping: dict[Gesture, Action] = field(default_factory=_default_mapping)

    def action_for(self, gesture: Gesture) -> Action:
        return self.mapping.get(gesture, Action.NONE)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GestureMappingConfig:
        raw = data.get("mapping", {}) or {}
        mapping = _default_mapping()
        for key, value in raw.items():
            try:
                mapping[Gesture(key)] = Action(value)
            except ValueError as exc:
                raise InvalidConfigurationError(
                    f"invalid gesture mapping entry: {key!r} -> {value!r}"
                ) from exc
        return cls(mapping=mapping)


@dataclass
class CountdownConfig:
    enabled: bool = True
    seconds: int = 3

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CountdownConfig:
        return cls(
            enabled=bool(_get(data, "enabled", True)),
            seconds=int(_get(data, "seconds", 3)),
        )


@dataclass
class BurstConfig:
    count: int = 5
    delay_ms: int = 300

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BurstConfig:
        return cls(
            count=int(_get(data, "count", 5)),
            delay_ms=int(_get(data, "delay_ms", 300)),
        )


@dataclass
class FaceConfig:
    require_face: bool = True
    allow_multiple_faces: bool = False
    min_face_area_ratio: float = 0.03
    max_face_area_ratio: float = 0.55
    center_tolerance: float = 0.22
    require_smile: bool = False
    validate_eyes: bool = True
    ear_threshold: float = 0.18
    smile_threshold: float = 0.55

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FaceConfig:
        return cls(
            require_face=bool(_get(data, "require_face", True)),
            allow_multiple_faces=bool(_get(data, "allow_multiple_faces", False)),
            min_face_area_ratio=float(_get(data, "min_face_area_ratio", 0.03)),
            max_face_area_ratio=float(_get(data, "max_face_area_ratio", 0.55)),
            center_tolerance=float(_get(data, "center_tolerance", 0.22)),
            require_smile=bool(_get(data, "require_smile", False)),
            validate_eyes=bool(_get(data, "validate_eyes", True)),
            ear_threshold=float(_get(data, "ear_threshold", 0.18)),
            smile_threshold=float(_get(data, "smile_threshold", 0.55)),
        )


@dataclass
class QualityConfig:
    reject_blurry: bool = True
    blur_threshold: float = 100.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QualityConfig:
        return cls(
            reject_blurry=bool(_get(data, "reject_blurry", True)),
            blur_threshold=float(_get(data, "blur_threshold", 100.0)),
        )


@dataclass
class EnhancementConfig:
    enabled: bool = False
    auto_contrast: bool = True
    contrast: float = 1.08
    brightness: float = 1.03
    sharpen: float = 1.15

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnhancementConfig:
        return cls(
            enabled=bool(_get(data, "enabled", False)),
            auto_contrast=bool(_get(data, "auto_contrast", True)),
            contrast=float(_get(data, "contrast", 1.08)),
            brightness=float(_get(data, "brightness", 1.03)),
            sharpen=float(_get(data, "sharpen", 1.15)),
        )


@dataclass
class BackgroundConfig:
    enabled: bool = False
    model: str = "u2net"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BackgroundConfig:
        return cls(
            enabled=bool(_get(data, "enabled", False)),
            model=str(_get(data, "model", "u2net")),
        )


@dataclass
class BestShotConfig:
    keep_best_only: bool = True
    sharpness: float = 0.35
    brightness: float = 0.20
    face: float = 0.20
    smile: float = 0.15
    eyes: float = 0.10
    sharpness_reference: float = 500.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BestShotConfig:
        return cls(
            keep_best_only=bool(_get(data, "keep_best_only", True)),
            sharpness=float(_get(data, "sharpness", 0.35)),
            brightness=float(_get(data, "brightness", 0.20)),
            face=float(_get(data, "face", 0.20)),
            smile=float(_get(data, "smile", 0.15)),
            eyes=float(_get(data, "eyes", 0.10)),
            sharpness_reference=float(_get(data, "sharpness_reference", 500.0)),
        )


@dataclass
class AudioConfig:
    voice_enabled: bool = True
    rate: int = 170
    volume: float = 1.0
    voice_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AudioConfig:
        voice_id = data.get("voice_id")
        return cls(
            voice_enabled=bool(_get(data, "voice_enabled", True)),
            rate=int(_get(data, "rate", 170)),
            volume=float(_get(data, "volume", 1.0)),
            voice_id=str(voice_id) if voice_id else None,
        )


@dataclass
class StorageConfig:
    save_folder: str = field(default_factory=lambda: str(paths.default_captures_dir()))
    image_format: str = "jpg"
    jpeg_quality: int = 92

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StorageConfig:
        folder = data.get("save_folder") or str(paths.default_captures_dir())
        return cls(
            save_folder=str(folder),
            image_format=str(_get(data, "image_format", "jpg")).lower(),
            jpeg_quality=int(_get(data, "jpeg_quality", 92)),
        )


@dataclass
class AppConfig:
    """Root application configuration."""

    theme: str = "system"
    language: str = "en"
    log_level: str = "INFO"
    camera: CameraConfig = field(default_factory=CameraConfig)
    recognition: RecognitionConfig = field(default_factory=RecognitionConfig)
    gestures: GestureMappingConfig = field(default_factory=GestureMappingConfig)
    countdown: CountdownConfig = field(default_factory=CountdownConfig)
    burst: BurstConfig = field(default_factory=BurstConfig)
    face: FaceConfig = field(default_factory=FaceConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    enhancement: EnhancementConfig = field(default_factory=EnhancementConfig)
    background: BackgroundConfig = field(default_factory=BackgroundConfig)
    best_shot: BestShotConfig = field(default_factory=BestShotConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppConfig:
        data = data or {}
        return cls(
            theme=str(_get(data, "theme", "system")),
            language=str(_get(data, "language", "en")),
            log_level=str(_get(data, "log_level", "INFO")).upper(),
            camera=CameraConfig.from_dict(data.get("camera", {})),
            recognition=RecognitionConfig.from_dict(data.get("recognition", {})),
            gestures=GestureMappingConfig.from_dict(data.get("gestures", {})),
            countdown=CountdownConfig.from_dict(data.get("countdown", {})),
            burst=BurstConfig.from_dict(data.get("burst", {})),
            face=FaceConfig.from_dict(data.get("face", {})),
            quality=QualityConfig.from_dict(data.get("quality", {})),
            enhancement=EnhancementConfig.from_dict(data.get("enhancement", {})),
            background=BackgroundConfig.from_dict(data.get("background", {})),
            best_shot=BestShotConfig.from_dict(data.get("best_shot", {})),
            audio=AudioConfig.from_dict(data.get("audio", {})),
            storage=StorageConfig.from_dict(data.get("storage", {})),
        )

    def validate(self) -> None:
        """Validate value ranges, raising :class:`InvalidConfigurationError`."""
        _require(
            self.camera.width > 0 and self.camera.height > 0, "camera dimensions must be positive"
        )
        _require(self.camera.fps > 0, "camera fps must be positive")
        _require(self.recognition.max_hands >= 1, "max_hands must be >= 1")
        _require(
            self.recognition.min_consistent_frames >= 1,
            "min_consistent_frames must be >= 1",
        )
        _require(
            self.recognition.min_consistent_frames <= self.recognition.window_size,
            "min_consistent_frames cannot exceed window_size",
        )
        _require(
            0.0 <= self.recognition.min_confidence <= 1.0,
            "min_confidence must be within [0, 1]",
        )
        _require(self.recognition.cooldown_seconds >= 0, "cooldown_seconds must be >= 0")
        _require(self.countdown.seconds >= 0, "countdown seconds must be >= 0")
        _require(self.burst.count >= 1, "burst count must be >= 1")
        _require(self.burst.delay_ms >= 0, "burst delay must be >= 0")
        _require(self.quality.blur_threshold >= 0, "blur_threshold must be >= 0")
        _require(
            0.0 < self.face.max_face_area_ratio <= 1.0,
            "max_face_area_ratio must be within (0, 1]",
        )
        _require(
            0.0 <= self.face.min_face_area_ratio < self.face.max_face_area_ratio,
            "min_face_area_ratio must be >= 0 and below max_face_area_ratio",
        )
        weight_sum = (
            self.best_shot.sharpness
            + self.best_shot.brightness
            + self.best_shot.face
            + self.best_shot.smile
            + self.best_shot.eyes
        )
        _require(weight_sum > 0, "best-shot weights must sum to a positive value")
        _require(
            self.storage.image_format in {"jpg", "jpeg", "png"}, "image_format must be jpg or png"
        )
        _require(1 <= self.storage.jpeg_quality <= 100, "jpeg_quality must be within [1, 100]")
        _require(0.0 <= self.audio.volume <= 1.0, "audio volume must be within [0, 1]")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidConfigurationError(message)
