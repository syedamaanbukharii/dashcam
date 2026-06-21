"""Loading, saving and defaulting of the application configuration.

:class:`ConfigManager` is the single entry point the rest of the app uses to
obtain an :class:`~gesturecam.config.schema.AppConfig`. User overrides live in a
JSON file; anything missing falls back to the typed defaults, and the merged
result is always validated before being handed out.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .. import paths
from ..errors import ConfigError, InvalidConfigurationError
from ..logging_setup import get_logger
from .schema import AppConfig

logger = get_logger(__name__)


class ConfigManager:
    """Reads and writes :class:`AppConfig` to a JSON file on disk."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._path = config_path or paths.config_file()

    @property
    def path(self) -> Path:
        return self._path

    @staticmethod
    def default_config() -> AppConfig:
        """Return a fresh configuration populated entirely with defaults."""
        config = AppConfig()
        config.validate()
        return config

    def load(self) -> AppConfig:
        """Load configuration from disk, merging over defaults.

        A missing file is not an error: the defaults are returned (and the
        caller may choose to persist them). A corrupt or invalid file raises
        :class:`ConfigError`.
        """
        if not self._path.exists():
            logger.info("No config file at %s; using defaults", self._path)
            return self.default_config()

        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(f"failed to read config at {self._path}: {exc}") from exc

        if not isinstance(raw, dict):
            raise ConfigError(f"config root must be a JSON object, got {type(raw).__name__}")

        config = AppConfig.from_dict(raw)
        try:
            config.validate()
        except InvalidConfigurationError:
            logger.exception("Configuration failed validation")
            raise
        logger.info("Loaded configuration from %s", self._path)
        return config

    def save(self, config: AppConfig) -> None:
        """Validate and atomically write ``config`` to disk as JSON."""
        config.validate()
        payload: dict[str, Any] = config.to_dict()
        paths.ensure_dir(self._path.parent)

        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        try:
            tmp.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")
            tmp.replace(self._path)
        except OSError as exc:
            raise ConfigError(f"failed to write config at {self._path}: {exc}") from exc
        logger.info("Saved configuration to %s", self._path)

    def load_or_create(self) -> AppConfig:
        """Load the config, creating the file from defaults if it is absent."""
        if not self._path.exists():
            config = self.default_config()
            self.save(config)
            return config
        return self.load()
