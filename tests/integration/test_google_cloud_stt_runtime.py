"""Integration tests for runtime-facing Phase 17 cloud STT behavior."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.command_models import CommandRecognitionResult
from core.stt import VoiceListener


@dataclass
class _Audio:
    payload: bytes = b"\x00\x01\x02\x03"

    def get_raw_data(self, *, convert_rate: int, convert_width: int) -> bytes:  # noqa: ARG002
        return self.payload


@dataclass
class _PreprocessingOutcome:
    raw_duration_ms: int = 1000
    processed_duration_ms: int = 900


def test_startup_is_safe_without_cloud_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EGB_STT_CLOUD_PRIMARY_ENABLED", "1")
    monkeypatch.setenv("EGB_STT_STRICT_VOSK_FALLBACK_ENABLED", "0")
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    listener = VoiceListener(default_language="en-US")
    state = listener.provider_availability_state()
    assert state["startup_safe"] is True
    assert state["availability"] == "unavailable"
    assert state["reason_code"] in {"cloud_credentials_missing", "cloud_client_import_missing"}
    assert callable(listener.listen_any)
    assert callable(listener.listen_command)
    assert callable(listener.listen_command_result)
    assert callable(listener.listen_command_window)


def test_listen_command_result_emits_cloud_primary_metadata_without_signature_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listener = VoiceListener(default_language="en-US")
    monkeypatch.setattr("core.stt.preprocess_audio_for_capture", lambda *_args, **_kwargs: _PreprocessingOutcome())
    monkeypatch.setattr(listener, "listen_audio", lambda **_kwargs: _Audio())
    monkeypatch.setattr(listener, "_analyze_vad_profile", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        listener,
        "_recognize_candidates",
        lambda *args, **kwargs: (  # noqa: ARG005
            "start obstacle detection",
            "en-US",
            ("start obstacle detection", "start obstacles"),
            0.92,
            {
                "recognition_source": "cloud_primary",
                "selected_language": "en-US",
                "detected_language": "en-US",
                "failure_reason_code": None,
            },
        ),
    )
    result = listener.listen_command_result(
        timeout_s=1,
        phrase_time_limit_s=1,
        languages=["en-US"],
        recognition_path="local_first",
        usage_mode="command",
    )
    assert isinstance(result, CommandRecognitionResult)
    assert result is not None
    assert result.primary_transcript == "start obstacle detection"
    assert result.recognition_source == "cloud_primary"
    assert result.selected_language == "en-US"


def test_detected_language_is_metadata_only_and_does_not_mutate_listener_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listener = VoiceListener(default_language="en-US")
    monkeypatch.setattr("core.stt.preprocess_audio_for_capture", lambda *_args, **_kwargs: _PreprocessingOutcome())
    monkeypatch.setattr(listener, "listen_audio", lambda **_kwargs: _Audio())
    monkeypatch.setattr(listener, "_analyze_vad_profile", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        listener,
        "_recognize_candidates",
        lambda *args, **kwargs: (  # noqa: ARG005
            "اقرأ النص",
            "ar-EG",
            ("اقرأ النص",),
            0.85,
            {
                "recognition_source": "cloud_primary",
                "selected_language": "en-US",
                "detected_language": "ar-EG",
                "failure_reason_code": None,
            },
        ),
    )
    result = listener.listen_command_result(
        timeout_s=1,
        phrase_time_limit_s=1,
        languages=["en-US", "ar-EG"],
        recognition_path="local_first",
        usage_mode="command",
    )
    assert result is not None
    assert result.detected_language == "ar-EG"
    assert result.selected_language == "en-US"
    assert listener.get_language() == "en-US"


def test_standby_wake_result_emits_wake_source_and_fallback_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listener = VoiceListener(default_language="en-US")
    monkeypatch.setattr("core.stt.preprocess_audio_for_capture", lambda *_args, **_kwargs: _PreprocessingOutcome())
    monkeypatch.setattr(listener, "listen_audio", lambda **_kwargs: _Audio())
    monkeypatch.setattr(listener, "_analyze_vad_profile", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        listener,
        "_recognize_candidates",
        lambda *args, **kwargs: (  # noqa: ARG005
            "hi egb",
            "en-US",
            ("hi egb",),
            0.88,
            {
                "recognition_source": "wake_strict_vosk_fallback",
                "selected_language": "en-US",
                "detected_language": "en-US",
                "failure_reason_code": "cloud_network_timeout",
            },
        ),
    )
    result = listener.listen_command_result(
        timeout_s=1,
        phrase_time_limit_s=1,
        languages=["en-US", "ar-EG"],
        recognition_path="local_first",
        usage_mode="standby_wake",
        capture_profile_id="standby_wake.default",
    )
    assert result is not None
    assert result.recognition_source == "wake_strict_vosk_fallback"
    assert result.failure_reason_code == "cloud_network_timeout"
    assert result.profile_id == "standby_wake.default"


def test_standby_wake_result_preserves_disabled_rollout_parity_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listener = VoiceListener(default_language="en-US")
    monkeypatch.setattr("core.stt.preprocess_audio_for_capture", lambda *_args, **_kwargs: _PreprocessingOutcome())
    monkeypatch.setattr(listener, "listen_audio", lambda **_kwargs: _Audio())
    monkeypatch.setattr(listener, "_analyze_vad_profile", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        listener,
        "_recognize_candidates",
        lambda *args, **kwargs: (  # noqa: ARG005
            "hi egb",
            "en-US",
            ("hi egb",),
            None,
            {
                "recognition_source": "local_vosk",
                "selected_language": "en-US",
                "detected_language": "en-US",
                "failure_reason_code": None,
            },
        ),
    )
    result = listener.listen_command_result(
        timeout_s=1,
        phrase_time_limit_s=1,
        languages=["en-US", "ar-EG"],
        recognition_path="local_first",
        usage_mode="standby_wake",
        capture_profile_id="standby_wake.default",
    )
    assert result is not None
    assert result.recognition_source == "local_vosk"
    assert result.failure_reason_code is None
