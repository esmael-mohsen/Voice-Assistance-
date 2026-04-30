"""Unit tests for Phase 19 cloud-primary wake recognition behavior."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.speech.google_cloud_stt import CloudRecognitionCandidate
from core.stt import VoiceListener
from core.wake_word import detect_wake


@dataclass
class _Audio:
    payload: bytes = b"\x00\x01"

    def get_raw_data(self, *, convert_rate: int, convert_width: int) -> bytes:  # noqa: ARG002
        return self.payload


def _recognized_cloud_wake(
    text: str,
    *,
    alternatives: tuple[str, ...] = (),
    confidence: float = 0.91,
) -> CloudRecognitionCandidate:
    merged = (text, *alternatives)
    return CloudRecognitionCandidate(
        provider_source="cloud_primary",
        status="recognized",
        recognition_path="local_first",
        primary_transcript=text,
        confidence_available=True,
        confidence_score=confidence,
        alternative_transcripts=merged,
        selected_language="en-US",
        detected_language="en-US",
        latency_ms=120,
        failure_reason_code=None,
    )


def _failed_cloud_wake(reason: str = "cloud_network_timeout") -> CloudRecognitionCandidate:
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
        latency_ms=950,
        failure_reason_code=reason,
    )


@pytest.fixture()
def wake_listener(monkeypatch: pytest.MonkeyPatch) -> VoiceListener:
    monkeypatch.setenv("EGB_STT_CLOUD_PRIMARY_ENABLED", "1")
    monkeypatch.setenv("EGB_STT_STRICT_VOSK_FALLBACK_ENABLED", "1")
    monkeypatch.setenv("EGB_STT_ENABLE_SPHINX_COMPAT", "0")
    return VoiceListener(default_language="en-US")


def _recognize_standby_wake(listener: VoiceListener) -> list[tuple[str, float | None, str, dict[str, object]]]:
    return listener._recognize_audio_candidates(
        _Audio(),
        language_code="en-US",
        for_command=False,
        usage_mode="standby_wake",
        recognition_path="local_first",
        closed_vocabulary_id=None,
        closed_vocabulary_choices=None,
    )


def test_cloud_primary_standby_wake_candidates_preserve_metadata(
    wake_listener: VoiceListener,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        wake_listener,
        "_recognize_cloud_candidate",
        lambda **_kwargs: _recognized_cloud_wake("hi egb open navigation", alternatives=("hi egb",)),
    )

    candidates = _recognize_standby_wake(wake_listener)
    assert len(candidates) == 2
    assert candidates[0][0] == "hi egb open navigation"
    assert candidates[0][2] == "cloud_primary"
    assert candidates[1][0] == "hi egb"
    assert candidates[0][3]["recognition_source"] == "cloud_primary"
    assert candidates[0][3]["selected_language"] == "en-US"
    assert candidates[0][3]["detected_language"] == "en-US"
    assert candidates[0][3]["failure_reason_code"] is None


def test_cloud_timeout_uses_wake_strict_fallback_in_standby_mode(
    wake_listener: VoiceListener,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(wake_listener, "_recognize_cloud_candidate", lambda **_kwargs: _failed_cloud_wake())
    monkeypatch.setattr(
        wake_listener,
        "_recognize_vosk_candidates",
        lambda *_args, **kwargs: [("hi egb", 0.82)] if kwargs.get("strict_mode") else [],
    )

    candidates = _recognize_standby_wake(wake_listener)
    assert candidates
    assert candidates[0][0] == "hi egb"
    assert candidates[0][2] == "wake_strict_vosk_fallback"
    assert candidates[0][3]["recognition_source"] == "wake_strict_vosk_fallback"
    assert candidates[0][3]["cloud_failure_reason_code"] == "cloud_network_timeout"


def test_cloud_timeout_without_strict_match_reports_no_wake(
    wake_listener: VoiceListener,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(wake_listener, "_recognize_cloud_candidate", lambda **_kwargs: _failed_cloud_wake())
    monkeypatch.setattr(wake_listener, "_recognize_vosk_candidates", lambda *_args, **_kwargs: [])

    candidates = _recognize_standby_wake(wake_listener)
    assert candidates == []
    assert wake_listener.last_error == "strict_grammar_no_match"


def test_standby_wake_strict_fallback_uses_wake_grammar_inventory(
    wake_listener: VoiceListener,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _capture_grammar(*_args, **kwargs):
        captured["strict_mode"] = kwargs.get("strict_mode")
        captured["grammar_phrases"] = kwargs.get("grammar_phrases")
        return []

    monkeypatch.setattr(wake_listener, "_recognize_cloud_candidate", lambda **_kwargs: _failed_cloud_wake())
    monkeypatch.setattr(wake_listener, "_recognize_vosk_candidates", _capture_grammar)

    _recognize_standby_wake(wake_listener)
    assert captured["strict_mode"] is True
    grammar = captured.get("grammar_phrases")
    assert isinstance(grammar, tuple)
    assert "hi egb" in grammar
    assert "marhaba" in grammar


@pytest.mark.parametrize("transcript", ("open navigation", "hello assistant", "highway gps"))
def test_unrelated_or_command_only_cloud_transcripts_fail_canonical_wake_gate(transcript: str) -> None:
    decision = detect_wake(transcript)
    assert decision.accepted is False
