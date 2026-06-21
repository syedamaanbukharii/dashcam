"""Theme constants and appearance configuration for the CustomTkinter UI.

Centralising colours, fonts and spacing keeps the widget code free of magic
values and makes the look consistent and easy to retune.
"""

from __future__ import annotations

import customtkinter as ctk

# Palette (hex strings consumed directly by CustomTkinter).
ACCENT = "#3B82F6"
ACCENT_HOVER = "#2563EB"
SUCCESS = "#22C55E"
WARNING = "#F59E0B"
ERROR = "#EF4444"
SURFACE = "#1F2937"
SURFACE_MUTED = "#111827"
TEXT_PRIMARY = "#F9FAFB"
TEXT_MUTED = "#9CA3AF"

# Typography (family, size, weight tuples are built lazily via font()).
FONT_FAMILY = "Helvetica"
TITLE_SIZE = 20
BODY_SIZE = 13
COUNTDOWN_SIZE = 160

# Spacing scale.
PAD_S = 4
PAD_M = 8
PAD_L = 16

_VALID_MODES = {"system", "light", "dark"}


def apply_appearance(theme: str) -> None:
    """Apply the configured appearance mode and default colour theme."""
    mode = theme if theme in _VALID_MODES else "system"
    ctk.set_appearance_mode(mode)
    ctk.set_default_color_theme("blue")


def font(size: int = BODY_SIZE, *, bold: bool = False) -> ctk.CTkFont:
    """Build a :class:`CTkFont`; must be called after a root window exists."""
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight="bold" if bold else "normal")


def level_color(level: str) -> str:
    """Map a status level to a palette colour."""
    return {"info": TEXT_MUTED, "warning": WARNING, "error": ERROR}.get(level, TEXT_MUTED)
