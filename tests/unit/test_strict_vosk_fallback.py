"""Unit tests for strict Vosk fallback behavior."""

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
def strict_listener(monkeypatch: pytest.MonkeyPatch) -> VoiceListener:
    monkeypatch.setenv("EGB_STT_CLOUD_PRIMARY_ENABLED", "1")
    monkeypatch.setenv("EGB_STT_STRICT_VOSK_FALLBACK_ENABLED", "1")
    monkeypatch.setenv("EGB_STT_ENABLE_SPHINX_COMPAT", "0")
    return VoiceListener(default_language="en-US")


def _failed_cloud_candidate() -> CloudRecognitionCandidate:
    return CloudRecognitionCandidate(
        provider_source="cloud_primary",
        status="failed",
        recognition_path="local_first",
        primary_transcript=None,
        confidence_available=False,
        confidence_score=None,
        alternative_transcripts=(),
        selected_language="en-US",
        detected_language=None,
        latency_ms=1200,
        failure_reason_code="cloud_network_timeout",
    )


def _cloud_candidate_with_failure(reason_code: str) -> CloudRecognitionCandidate:
    return CloudRecognitionCandidate(
        provider_source="cloud_primary",
        status="failed",
        recognition_path="local_first",
        primary_transcript=None,
        confidence_available=False,
        confidence_score=None,
        alternative_transcripts=(),
        selected_language="en-US",
        detected_language=None,
        latency_ms=1200,
        failure_reason_code=reason_code,
    )


def test_strict_fallback_uses_command_inventory_when_cloud_fails(
    strict_listener: VoiceListener,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(strict_listener, "_recognize_cloud_candidate", lambda **_kwargs: _failed_cloud_candidate())
    monkeypatch.setattr(
        strict_listener,
        "_recognize_vosk_candidates",
        lambda *args, **kwargs: [("start obstacle detection", 0.82)] if kwargs.get("strict_mode") else [],
    )
    candidates = strict_listener._recognize_audio_candidates(
        _Audio(),
        language_code="en-US",
        for_command=True,
        usage_mode="command",
        recognition_path="local_first",
        closed_vocabulary_id=None,
        closed_vocabulary_choices=None,
    )
    assert candidates
    assert candidates[0][2] == "strict_vosk_fallback"
    assert candidates[0][0] == "start obstacle detection"


def test_strict_fallback_returns_no_match_when_grammar_does_not_match(
    strict_listener: VoiceListener,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(strict_listener, "_recognize_cloud_candidate", lambda **_kwargs: _failed_cloud_candidate())
    monkeypatch.setattr(
        strict_listener,
        "_recognize_vosk_candidates",
        lambda *args, **kwargs: [],
    )
    candidates = strict_listener._recognize_audio_candidates(
        _Audio(),
        language_code="en-US",
        for_command=True,
        usage_mode="command",
        recognition_path="local_first",
        closed_vocabulary_id=None,
        closed_vocabulary_choices=None,
    )
    assert candidates == []
    assert strict_listener.last_error == "strict_grammar_no_match"


@pytest.mark.parametrize(
    ("failure_reason", "expected_error"),
    [
        ("cloud_network_timeout", "strict_grammar_no_match"),
        ("cloud_empty_result", "strict_grammar_no_match"),
        ("cloud_service_unavailable", "strict_grammar_no_match"),
    ],
)
def test_strict_fallback_triggers_on_common_cloud_failure_states(
    strict_listener: VoiceListener,
    monkeypatch: pytest.MonkeyPatch,
    failure_reason: str,
    expected_error: str,
) -> None:
    monkeypatch.setattr(
        strict_listener,
        "_recognize_cloud_candidate",
        lambda **_kwargs: _cloud_candidate_with_failure(failure_reason),
    )
    monkeypatch.setattr(strict_listener, "_recognize_vosk_candidates", lambda *args, **kwargs: [])
    candidates = strict_listener._recognize_audio_candidates(
        _Audio(),
        language_code="en-US",
        for_command=True,
        usage_mode="command",
        recognition_path="local_first",
        closed_vocabulary_id=None,
        closed_vocabulary_choices=None,
    )
    assert candidates == []
    assert strict_listener.last_error == expected_error


def test_strict_fallback_mode_closed_choice_uses_supplied_choices(strict_listener: VoiceListener) -> None:
    phrases = strict_listener._strict_grammar_phrases(
        mode="closed_choice",
        usage_mode="confirmation",
        closed_vocabulary_choices=("yes", "no", "cancel"),
        closed_vocabulary_id="confirmation.yes_no",
    )
    assert phrases == ("yes", "no", "cancel")


def test_strict_fallback_mode_wake_grammar_has_deterministic_aliases(strict_listener: VoiceListener) -> None:
    phrases = strict_listener._strict_grammar_phrases(
        mode="wake_grammar",
        usage_mode="standby_wake",
        closed_vocabulary_choices=None,
        closed_vocabulary_id=None,
    )
    assert "hi egb" in phrases
    assert "marhaba" in phrases


def test_standby_wake_strict_fallback_rejects_command_only_phrases(
    strict_listener: VoiceListener,
) -> None:
    phrases = strict_listener._strict_grammar_phrases(
        mode="wake_grammar",
        usage_mode="standby_wake",
        closed_vocabulary_choices=None,
        closed_vocabulary_id=None,
    )
    assert "open navigation" not in phrases
