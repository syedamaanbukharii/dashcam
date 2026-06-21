"""Turning a candidate frame into a saved, recorded capture.

This service owns the post-detection pipeline: evaluate quality, reject frames
that fail the configured gates (blur / eyes-closed / no-smile / no-face),
optionally enhance and remove the background, write the image with Pillow and
record it in the database. It deliberately does no threading or event work -
the engine orchestrates it - so the logic stays straightforward and testable.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from ..audio.tts import Voice
from ..config.schema import AppConfig
from ..errors import StorageError
from ..face import average_ear, smile_ratio
from ..face.detector import FaceDetection
from ..logging_setup import get_logger
from ..paths import ensure_dir
from ..quality import FrameQuality, ShotScoreWeights, best_index, enhance, variance_of_laplacian
from ..quality.enhancement import EnhancementSettings
from ..quality.metrics import mean_brightness
from ..storage.database import CaptureDatabase
from ..storage.models import CaptureRecord

if TYPE_CHECKING:  # pragma: no cover - typing only
    from PIL import Image

logger = get_logger(__name__)


@dataclass(slots=True)
class CaptureOutcome:
    """Result of attempting a single capture."""

    record: CaptureRecord | None
    quality: FrameQuality
    rejected_reason: str | None = None

    @property
    def saved(self) -> bool:
        return self.record is not None


@dataclass(slots=True)
class BurstOutcome:
    """Result of a burst: everything saved plus which was the best."""

    saved: list[CaptureRecord] = field(default_factory=list)
    best: CaptureRecord | None = None
    evaluated: int = 0


class CaptureService:
    """Validates, enhances and persists captured frames."""

    def __init__(self, config: AppConfig, database: CaptureDatabase, voice: Voice) -> None:
        self._config = config
        self._db = database
        self._voice = voice

    # -- quality -----------------------------------------------------------
    def evaluate(self, image_bgr: NDArray[np.uint8], faces: list[FaceDetection]) -> FrameQuality:
        """Compute the full :class:`FrameQuality` for a frame."""
        sharpness = variance_of_laplacian(image_bgr)
        brightness = mean_brightness(image_bgr)
        face_visible = 1.0 if faces else 0.0
        smile = 0.0
        eyes = 0.0
        face = self._largest_face(faces)
        if face is not None and face.mesh is not None:
            smile = smile_ratio(face.mesh)
            ear = average_ear(face.mesh)
            threshold = self._config.face.ear_threshold
            eyes = min(1.0, ear / threshold) if threshold > 0 else 0.0
        return FrameQuality(
            sharpness=sharpness,
            brightness=brightness,
            face_visible=face_visible,
            smile=smile,
            eyes_open=eyes,
        )

    def rejection_reason(self, quality: FrameQuality, faces: list[FaceDetection]) -> str | None:
        """Return a human reason the frame should be rejected, or ``None``."""
        cfg = self._config
        if cfg.quality.reject_blurry and quality.sharpness < cfg.quality.blur_threshold:
            return "Too blurry"
        if cfg.face.require_face and not faces:
            return "No face detected"
        if cfg.face.validate_eyes and faces:
            face = self._largest_face(faces)
            if (
                face is not None
                and face.mesh is not None
                and average_ear(face.mesh) < cfg.face.ear_threshold
            ):
                return "Eyes closed"
        if cfg.face.require_smile and faces:
            face = self._largest_face(faces)
            if (
                face is not None
                and face.mesh is not None
                and smile_ratio(face.mesh) < cfg.face.smile_threshold
            ):
                return "Waiting for a smile"
        return None

    # -- capture -----------------------------------------------------------
    def process_single(
        self, image_bgr: NDArray[np.uint8], faces: list[FaceDetection]
    ) -> CaptureOutcome:
        """Validate and, if it passes, save a single photo."""
        quality = self.evaluate(image_bgr, faces)
        reason = self.rejection_reason(quality, faces)
        if reason is not None:
            logger.info("Capture rejected: %s", reason)
            return CaptureOutcome(record=None, quality=quality, rejected_reason=reason)
        record = self._persist(image_bgr, quality, media_type="photo")
        self._voice.say("Photo saved")
        return CaptureOutcome(record=record, quality=quality)

    def process_burst(
        self, frames: list[tuple[NDArray[np.uint8], list[FaceDetection]]]
    ) -> BurstOutcome:
        """Score every frame in a burst and keep the best (or all)."""
        if not frames:
            return BurstOutcome()

        qualities = [self.evaluate(image, faces) for image, faces in frames]
        weights = self._weights()
        reference = self._config.best_shot.sharpness_reference
        best = best_index(qualities, weights, sharpness_reference=reference)

        outcome = BurstOutcome(evaluated=len(frames))
        if self._config.best_shot.keep_best_only:
            image, _faces = frames[best]
            record = self._persist(image, qualities[best], media_type="photo")
            outcome.saved.append(record)
            outcome.best = record
        else:
            for offset, (image, _faces) in enumerate(frames):
                record = self._persist(image, qualities[offset], media_type="photo")
                outcome.saved.append(record)
                if offset == best:
                    outcome.best = record
        self._voice.say("Photo saved")
        return outcome

    def register_video(self, path: Path, *, width: int, height: int) -> CaptureRecord:
        """Record an already-written video file in the database."""
        record = CaptureRecord(
            filename=path.name,
            path=str(path),
            media_type="video",
            created_at=_now_iso(),
            width=width,
            height=height,
            metadata={"source": "gesture-recording"},
        )
        return self._db.add(record)

    # -- internals ---------------------------------------------------------
    def _persist(
        self, image_bgr: NDArray[np.uint8], quality: FrameQuality, *, media_type: str
    ) -> CaptureRecord:

        image = self._to_pil(image_bgr)
        image = enhance(image, self._enhancement_settings())

        fmt = self._config.storage.image_format.lower()
        if self._config.background.enabled:
            removed = self._remove_background(image)
            if removed is not None:
                image = removed
                fmt = "png"  # preserve transparency

        folder = Path(self._config.storage.save_folder)
        ensure_dir(folder)
        filename = _timestamped_name(fmt)
        target = folder / filename
        try:
            self._save_image(image, target, fmt)
        except (OSError, ValueError) as exc:
            raise StorageError(f"failed to save capture to {target}: {exc}") from exc

        record = CaptureRecord(
            filename=filename,
            path=str(target),
            media_type=media_type,
            created_at=_now_iso(),
            score=round(self._score(quality), 4),
            width=image.width,
            height=image.height,
            metadata={
                "sharpness": round(quality.sharpness, 2),
                "brightness": round(quality.brightness, 2),
                "smile": round(quality.smile, 3),
                "eyes_open": round(quality.eyes_open, 3),
            },
        )
        logger.info("Saved capture %s (score=%.3f)", filename, record.score)
        return self._db.add(record)

    def _save_image(self, image: Image.Image, target: Path, fmt: str) -> None:
        if fmt in {"jpg", "jpeg"}:
            rgb = image.convert("RGB")
            rgb.save(target, format="JPEG", quality=self._config.storage.jpeg_quality)
        else:
            image.save(target, format="PNG")

    def _remove_background(self, image: Image.Image) -> Image.Image | None:
        try:
            from rembg import remove
        except ImportError:
            logger.warning("rembg not installed; skipping background removal")
            return None
        try:  # pragma: no cover - heavy optional dependency
            return remove(image)
        except Exception:  # noqa: BLE001
            logger.exception("Background removal failed; keeping original")
            return None

    @staticmethod
    def _to_pil(image_bgr: NDArray[np.uint8]) -> Image.Image:
        from PIL import Image

        if image_bgr.ndim == 3 and image_bgr.shape[2] == 3:
            rgb = np.ascontiguousarray(image_bgr[:, :, ::-1])
        else:
            rgb = image_bgr
        return Image.fromarray(rgb)

    def _enhancement_settings(self) -> EnhancementSettings:
        cfg = self._config.enhancement
        return EnhancementSettings(
            enabled=cfg.enabled,
            auto_contrast=cfg.auto_contrast,
            contrast=cfg.contrast,
            brightness=cfg.brightness,
            sharpen=cfg.sharpen,
        )

    def _weights(self) -> ShotScoreWeights:
        cfg = self._config.best_shot
        return ShotScoreWeights(
            sharpness=cfg.sharpness,
            brightness=cfg.brightness,
            face=cfg.face,
            smile=cfg.smile,
            eyes=cfg.eyes,
        )

    def _score(self, quality: FrameQuality) -> float:
        from ..quality import score_shot

        return score_shot(
            quality,
            self._weights(),
            sharpness_reference=self._config.best_shot.sharpness_reference,
        )

    @staticmethod
    def _largest_face(faces: list[FaceDetection]) -> FaceDetection | None:
        if not faces:
            return None
        return max(faces, key=lambda f: f.box.area)


def _now_iso() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def _timestamped_name(fmt: str) -> str:
    ext = "jpg" if fmt in {"jpg", "jpeg"} else "png"
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    return f"photo_{stamp}.{ext}"
