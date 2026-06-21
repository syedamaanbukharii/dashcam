"""Exception hierarchy for GestureCam Pro.

A single rooted hierarchy makes it easy for the application shell to catch
broad categories (``GestureCamError``) while still allowing callers to react
to specific, recoverable conditions (camera unavailable, missing model,
disk full, ...).
"""

from __future__ import annotations


class GestureCamError(Exception):
    """Base class for every error raised by the application."""


# --- Configuration -----------------------------------------------------------
class ConfigError(GestureCamError):
    """Base class for configuration problems."""


class InvalidConfigurationError(ConfigError):
    """Raised when a configuration value fails validation."""


# --- Camera ------------------------------------------------------------------
class CameraError(GestureCamError):
    """Base class for camera problems."""


class CameraUnavailableError(CameraError):
    """Raised when the requested camera cannot be opened or read."""


# --- Models / ML dependencies ------------------------------------------------
class ModelError(GestureCamError):
    """Base class for model-related problems."""


class MissingModelError(ModelError):
    """Raised when a required model file is absent and cannot be downloaded."""


class DependencyError(GestureCamError):
    """Raised when an optional runtime dependency is not installed."""


# --- Storage / filesystem ----------------------------------------------------
class StorageError(GestureCamError):
    """Base class for storage problems."""


class DiskFullError(StorageError):
    """Raised when a write fails because the device is out of space."""


class PermissionDeniedError(GestureCamError):
    """Raised when the OS denies access to a resource (camera, file, ...)."""
