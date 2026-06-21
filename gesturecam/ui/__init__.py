"""CustomTkinter user interface.

This package's modules import CustomTkinter at module load, so the package
``__init__`` stays deliberately import-light: it exposes :class:`GestureCamApp`
lazily via :func:`__getattr__` so ``import gesturecam.ui`` does not require
CustomTkinter unless the window is actually constructed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .app import GestureCamApp

__all__ = ["GestureCamApp"]


def __getattr__(name: str) -> Any:
    if name == "GestureCamApp":
        from .app import GestureCamApp

        return GestureCamApp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
