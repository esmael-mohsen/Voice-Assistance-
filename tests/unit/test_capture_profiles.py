"""Unit coverage for Phase 14 capture and qualification profiles."""

from __future__ import annotations

import pytest

from core.audio.profiles import default_capture_profiles, select_capture_profile
from core.command_models import AudioCaptureProfile, SpeechQualificationProfile
from settings.profile_store import profile_from_snapshot


def test_default_capture_profiles_cover_all_runtime_modes() -> None:
    profiles = default_capture_profiles()
    assert {"standby_wake.default", "onboarding.default", "command.default", "confirmation.default"} <= set(
        profiles.keys()
    )
    assert profiles["command.default"].usage_mode == "command"
    assert profiles["confirmation.default"].dictionary_bias_mode == "closed_choice"


def test_audio_capture_profile_requires_closed_vocabulary_for_closed_choice() -> None:
    with pytest.raises(ValueError):
        AudioCaptureProfile(
            profile_id="confirmation.default",
            usage_mode="confirmation",
            dictionary_bias_mode="closed_choice",
            closed_vocabulary_id=None,
        )


def test_select_capture_profile_applies_simplified_qualification_constraints() -> None:
    profile = select_capture_profile(
        usage_mode="command",
        qualification_profile="simplified",
        allow_noise_suppression=True,
    )
    assert profile.usage_mode == "command"
    assert profile.allow_noise_suppression is False
    assert profile.max_utterance_ms <= 7000


def test_profile_store_preserves_phase14_profile_fields() -> None:
    loaded = profile_from_snapshot(
        {
            "username": "Tester",
            "command_capture_profile_id": "command.default",
            "confirmation_capture_profile_id": "confirmation.default",
            "speech_qualification_profile": "simplified",
            "enable_capture_relisten": True,
            "enable_dictionary_bias": True,
            "command_rescue_enabled": True,
        }
    )
    assert loaded.command_capture_profile_id == "command.default"
    assert loaded.confirmation_capture_profile_id == "confirmation.default"
    assert loaded.speech_qualification_profile == "simplified"
    assert loaded.command_rescue_enabled is True


def test_speech_qualification_profile_demoted_requires_reason() -> None:
    with pytest.raises(ValueError):
        SpeechQualificationProfile(
            qualification_profile_id="pi4.default",
            profile_label="default",
            enable_noise_suppression=True,
            enable_rescue_recognition=True,
            enable_dictionary_bias=True,
            enable_capture_relisten=True,
            qualification_status="demoted",
            demotion_reason="",
        )

