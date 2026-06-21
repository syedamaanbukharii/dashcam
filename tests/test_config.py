"""Tests for the configuration schema and manager."""

from __future__ import annotations

import json

import pytest

from gesturecam.config.manager import ConfigManager
from gesturecam.config.schema import AppConfig
from gesturecam.errors import ConfigError, InvalidConfigurationError
from gesturecam.gestures.types import Action, Gesture


def test_default_config_is_valid() -> None:
    config = ConfigManager.default_config()
    config.validate()  # must not raise
    assert config.camera.width > 0
    assert config.storage.image_format in {"jpg", "jpeg", "png"}


def test_round_trip_to_and_from_dict() -> None:
    config = ConfigManager.default_config()
    restored = AppConfig.from_dict(config.to_dict())
    assert restored.to_dict() == config.to_dict()


def test_from_dict_merges_over_defaults() -> None:
    data = {"camera": {"index": 3}, "audio": {"voice_enabled": False}}
    config = AppConfig.from_dict(data)
    # Overridden values take effect…
    assert config.camera.index == 3
    assert config.audio.voice_enabled is False
    # …while unspecified values fall back to defaults.
    assert config.camera.width == ConfigManager.default_config().camera.width


def test_default_gesture_mapping() -> None:
    mapping = ConfigManager.default_config().gestures
    assert mapping.action_for(Gesture.PEACE) is Action.PHOTO
    assert mapping.action_for(Gesture.THUMBS_DOWN) is Action.EXIT
    assert mapping.action_for(Gesture.OPEN_PALM) is Action.NONE


def test_invalid_value_raises() -> None:
    config = ConfigManager.default_config()
    config.camera.width = 0
    with pytest.raises(InvalidConfigurationError):
        config.validate()


def test_invalid_face_area_ordering_raises() -> None:
    config = ConfigManager.default_config()
    config.face.min_face_area_ratio = 0.9
    config.face.max_face_area_ratio = 0.5
    with pytest.raises(InvalidConfigurationError):
        config.validate()


def test_manager_save_and_load_round_trip(tmp_path) -> None:
    path = tmp_path / "config.json"
    manager = ConfigManager(path)
    config = ConfigManager.default_config()
    config.camera.fps = 24
    manager.save(config)

    reloaded = ConfigManager(path).load()
    assert reloaded.camera.fps == 24


def test_manager_missing_file_returns_defaults(tmp_path) -> None:
    manager = ConfigManager(tmp_path / "does-not-exist.json")
    config = manager.load()
    assert config.to_dict() == ConfigManager.default_config().to_dict()


def test_manager_corrupt_file_raises(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{ this is not valid json", encoding="utf-8")
    with pytest.raises(ConfigError):
        ConfigManager(path).load()


def test_load_or_create_writes_file(tmp_path) -> None:
    path = tmp_path / "config.json"
    manager = ConfigManager(path)
    manager.load_or_create()
    assert path.exists()
    # The written file is valid JSON describing the defaults.
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "camera" in data
