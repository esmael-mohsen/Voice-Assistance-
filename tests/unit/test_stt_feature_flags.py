"""Unit tests for Phase 17 STT feature-flag defaults and gates."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.speech.google_cloud_stt import CloudRecognitionCandidate
from core.stt import VoiceListener


@dataclass
class _Audio:
    payload: bytes = b"\x00\x01"

    def get_raw_data(self, *, convert_rate: int, convert_width: int) -> bytes:  # noqa: ARG002
        return self.payload


@pytest.fixture()
def clear_phase17_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "EGB_STT_CLOUD_PRIMARY_ENABLED",
        "EGB_STT_STRICT_VOSK_FALLBACK_ENABLED",
        "EGB_STT_ENABLE_SPHINX_COMPAT",
        "EGB_STT_CLOUD_TIMEOUT_S",
        "EGB_STT_CLOUD_MAX_ALTERNATIVES",
    ):
        monkeypatch.delenv(name, raising=False)


def test_phase17_defaults_are_conservative(clear_phase17_env) -> None:
    listener = VoiceListener(default_language="en-US")
    snapshot = listener.recognition_configuration_snapshot()
    assert snapshot["cloud_primary_enabled"] is False
    assert snapshot["strict_vosk_fallback_enabled"] is False
    assert snapshot["sphinx_compat_enabled"] is False
    assert snapshot["cloud_timeout_s"] == pytest.approx(3.0)
    assert snapshot["cloud_max_alternatives"] == 3
    assert snapshot["field_safe"] is True
    assert snapshot["credential_material_present"] is False


def test_phase17_env_flags_apply_and_numeric_values_are_clamped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EGB_STT_CLOUD_PRIMARY_ENABLED", "1")
    monkeypatch.setenv("EGB_STT_STRICT_VOSK_FALLBACK_ENABLED", "1")
    monkeypatch.setenv("EGB_STT_ENABLE_SPHINX_COMPAT", "1")
    monkeypatch.setenv("EGB_STT_CLOUD_TIMEOUT_S", "-4")
    monkeypatch.setenv("EGB_STT_CLOUD_MAX_ALTERNATIVES", "0")
    listener = VoiceListener(default_language="en-US")
    snapshot = listener.recognition_configuration_snapshot()
    assert snapshot["cloud_primary_enabled"] is True
    assert snapshot["strict_vosk_fallback_enabled"] is True
    assert snapshot["sphinx_compat_enabled"] is True
    assert snapshot["cloud_timeout_s"] == pytest.approx(3.0)
    assert snapshot["cloud_max_alternatives"] == 3


def test_cloud_failure_with_strict_fallback_disabled_returns_no_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EGB_STT_CLOUD_PRIMARY_ENABLED", "1")
    monkeypatch.setenv("EGB_STT_STRICT_VOSK_FALLBACK_ENABLED", "0")
    listener = VoiceListener(default_language="en-US")
    monkeypatch.setattr(
        listener,
        "_recognize_cloud_candidate",
        lambda **_kwargs: CloudRecognitionCandidate(
            provider_source="cloud_primary",
            status="failed",
            recognition_path="local_first",
            primary_transcript=None,
            confidence_available=False,
            confidence_score=None,
            alternative_transcripts=(),
            selected_language="en-US",
            detected_language=None,
            latency_ms=3000,
            failure_reason_code="cloud_network_timeout",
        ),
    )
    candidates = listener._recognize_audio_candidates(
        _Audio(),
        language_code="en-US",
        for_command=True,
        usage_mode="command",
        recognition_path="local_first",
        closed_vocabulary_id=None,
        closed_vocabulary_choices=None,
    )
    assert candidates == []
    assert listener.last_error == "cloud_network_timeout"


def test_cloud_disabled_keeps_local_candidate_ordering_for_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EGB_STT_CLOUD_PRIMARY_ENABLED", "0")
    monkeypatch.setenv("EGB_STT_STRICT_VOSK_FALLBACK_ENABLED", "1")
    listener = VoiceListener(default_language="en-US")
    monkeypatch.setattr(
        listener,
        "_recognize_cloud_candidate",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("cloud path should be skipped")),
    )
    monkeypatch.setattr(
        listener,
        "_recognize_vosk_candidates",
        lambda *_args, **_kwargs: [
            ("start obstacle detection", 0.83),
            ("stop system", 0.78),
            ("read text", 0.65),
        ],
    )
    candidates = listener._recognize_audio_candidates(
        _Audio(),
        language_code="en-US",
        for_command=True,
        usage_mode="command",
        recognition_path="local_first",
        closed_vocabulary_id=None,
        closed_vocabulary_choices=None,
    )
    assert [item[0] for item in candidates[:3]] == [
        "start obstacle detection",
        "stop system",
        "read text",
    ]
    assert all(item[2] == "local_vosk" for item in candidates[:3])


def test_cloud_disabled_keeps_local_candidate_ordering_for_standby_wake(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EGB_STT_CLOUD_PRIMARY_ENABLED", "0")
    monkeypatch.setenv("EGB_STT_STRICT_VOSK_FALLBACK_ENABLED", "1")
    listener = VoiceListener(default_language="en-US")
    monkeypatch.setattr(
        listener,
        "_recognize_cloud_candidate",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("cloud wake path should be skipped")),
    )
    monkeypatch.setattr(
        listener,
        "_recognize_vosk_candidates",
        lambda *_args, **_kwargs: [("hi egb", 0.86)],
    )
    candidates = listener._recognize_audio_candidates(
        _Audio(),
        language_code="en-US",
        for_command=True,
        usage_mode="standby_wake",
        recognition_path="local_first",
        closed_vocabulary_id=None,
        closed_vocabulary_choices=None,
    )
    assert candidates
    assert candidates[0][0] == "hi egb"
    assert candidates[0][2] == "wake_strict_vosk_fallback"


def test_cloud_failure_keeps_strict_local_wake_fallback_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EGB_STT_CLOUD_PRIMARY_ENABLED", "1")
    monkeypatch.setenv("EGB_STT_STRICT_VOSK_FALLBACK_ENABLED", "1")
    listener = VoiceListener(default_language="en-US")
    monkeypatch.setattr(
        listener,
        "_recognize_cloud_candidate",
        lambda **_kwargs: CloudRecognitionCandidate(
            provider_source="cloud_primary",
            status="failed",
            recognition_path="local_first",
            primary_transcript=None,
            confidence_available=False,
            confidence_score=None,
            alternative_transcripts=(),
            selected_language="en-US",
            detected_language=None,
            latency_ms=3000,
            failure_reason_code="cloud_service_unavailable",
        ),
    )
    monkeypatch.setattr(
        listener,
        "_recognize_vosk_candidates",
        lambda *_args, **kwargs: [("hi egb", 0.81)] if kwargs.get("strict_mode") else [],
    )
    candidates = listener._recognize_audio_candidates(
        _Audio(),
        language_code="en-US",
        for_command=False,
        usage_mode="standby_wake",
        recognition_path="local_first",
        closed_vocabulary_id=None,
        closed_vocabulary_choices=None,
    )
    assert candidates
    assert candidates[0][2] == "wake_strict_vosk_fallback"
    assert candidates[0][3]["cloud_failure_reason_code"] == "cloud_service_unavailable"


def test_pocketsphinx_is_not_used_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EGB_STT_ENABLE_SPHINX_COMPAT", "0")
    listener = VoiceListener(default_language="en-US")
    monkeypatch.setattr(listener, "_recognize_vosk_candidates", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(listener, "_recognize_sphinx_candidate", lambda *_args, **_kwargs: "from sphinx")
    candidates = listener._recognize_audio_candidates(
        _Audio(),
        language_code="en-US",
        for_command=False,
        usage_mode="wake",
        recognition_path="local_first",
        closed_vocabulary_id=None,
        closed_vocabulary_choices=None,
    )
    assert candidates == []


def test_pocketsphinx_can_be_enabled_explicitly_for_compatibility(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EGB_STT_ENABLE_SPHINX_COMPAT", "1")
    listener = VoiceListener(default_language="en-US")
    monkeypatch.setattr(listener, "_recognize_vosk_candidates", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(listener, "_recognize_sphinx_candidate", lambda *_args, **_kwargs: "from sphinx")
    candidates = listener._recognize_audio_candidates(
        _Audio(),
        language_code="en-US",
        for_command=False,
        usage_mode="wake",
        recognition_path="local_first",
        closed_vocabulary_id=None,
        closed_vocabulary_choices=None,
    )
    assert candidates
    assert candidates[0][2] == "sphinx_compat"
