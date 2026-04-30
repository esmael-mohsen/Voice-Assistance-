"""Regression checks for first-run language defaults."""

import settings.settings_manager as settings_module
from settings.profile_store import profile_from_snapshot
from settings.settings_manager import SettingsManager


def test_settings_manager_defaults_to_english_language() -> None:
    manager = SettingsManager()
    assert manager.language == "en-US"


def test_profile_snapshot_defaults_to_english_language() -> None:
    profile = profile_from_snapshot({})
    assert profile.language == "en-US"


def test_load_user_profile_for_unconfigured_user_forces_english_default(monkeypatch) -> None:
    manager = SettingsManager()
    monkeypatch.setattr(
        settings_module,
        "load_profile_snapshot",
        lambda: {"username": "", "language": "ar-EG", "voice_gender": "female", "speech_speed": 1.0},
    )
    monkeypatch.setattr(settings_module, "save_profile_snapshot", lambda _snapshot: None)
    loaded = manager.load_user_profile()
    assert loaded is True
    assert manager.language == "en-US"


def test_load_user_profile_keeps_explicit_language_for_configured_user(monkeypatch) -> None:
    manager = SettingsManager()
    monkeypatch.setattr(
        settings_module,
        "load_profile_snapshot",
        lambda: {"username": "Tester", "language": "ar-EG", "voice_gender": "female", "speech_speed": 1.0},
    )
    monkeypatch.setattr(settings_module, "save_profile_snapshot", lambda _snapshot: None)
    loaded = manager.load_user_profile()
    assert loaded is True
    assert manager.language == "ar-EG"
