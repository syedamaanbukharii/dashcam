"""Optional, conservative auto-enhancement.

The goal is a gentle clean-up, never an aggressive 'Instagram' look, so every
adjustment factor is clamped to a modest range and sharpening uses a small,
low-radius unsharp mask. Enhancement operates on :class:`PIL.Image.Image`
objects and is a no-op when disabled.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

# Clamp ranges keep the result natural-looking ("must not overprocess").
_MIN_FACTOR = 0.8
_MAX_FACTOR = 1.4


@dataclass(frozen=True, slots=True)
class EnhancementSettings:
    """How much of each adjustment to apply (1.0 == no change)."""

    enabled: bool = False
    auto_contrast: bool = True
    contrast: float = 1.08
    brightness: float = 1.03
    sharpen: float = 1.15

    def clamped(self) -> EnhancementSettings:
        return EnhancementSettings(
            enabled=self.enabled,
            auto_contrast=self.auto_contrast,
            contrast=_clamp_factor(self.contrast),
            brightness=_clamp_factor(self.brightness),
            sharpen=_clamp_factor(self.sharpen),
        )


def _clamp_factor(value: float) -> float:
    return max(_MIN_FACTOR, min(_MAX_FACTOR, value))


def enhance(image: Image.Image, settings: EnhancementSettings) -> Image.Image:
    """Return a gently enhanced copy of *image* (or the original if disabled)."""
    if not settings.enabled:
        return image

    settings = settings.clamped()
    result = image.convert("RGB")

    if settings.auto_contrast:
        # cutoff=1 ignores the most extreme 1% per channel to avoid clipping.
        result = ImageOps.autocontrast(result, cutoff=1)

    if settings.brightness != 1.0:
        result = ImageEnhance.Brightness(result).enhance(settings.brightness)
    if settings.contrast != 1.0:
        result = ImageEnhance.Contrast(result).enhance(settings.contrast)
    if settings.sharpen != 1.0:
        amount = int((settings.sharpen - 1.0) * 100)
        if amount > 0:
            result = result.filter(ImageFilter.UnsharpMask(radius=1.2, percent=amount, threshold=2))
    return result
