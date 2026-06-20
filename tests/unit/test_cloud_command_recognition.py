"""Unit tests for Phase 18 cloud-primary command recognition behavior."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.speech.google_cloud_stt import CloudRecognitionCandidate
from core.stt import VoiceListener

_AR_READ_TEXT = "\u0627\u0642\u0631\u0623 \u0627\u0644\u0646\u0635"
_AR_OBSTACLE = "\u0627\u0643\u062a\u0634\u0641 \u0627\u0644\u0639\u0648\u0627\u0626\u0642"

_ARABIC_BILINGUAL_BASELINE_FIXTURES: tuple[tuple[str, str], ...] = (
    ("en-US", "start obstacle detection"),
    ("ar-EG", _AR_READ_TEXT),
    ("ar-EG", _AR_OBSTACLE),
    ("en-US", "help me"),
)

_COMMON_COMMAND_FIXTURES: tuple[str, ...] = (
    "start obstacle detection",
    "read text",
    "recognize face",
)


@dataclass
class _Audio:
    payload: bytes = b"\x00\x01"

    def get_raw_data(self, *, convert_rate: int, convert_width: int) -> bytes:  # noqa: ARG002
        return self.payload


def _recognized_candidate(
    primary_text: str,
    *,
    selected_language: str,
    detected_language: str | None = None,
    alternatives: tuple[str, ...] = (),
    confidence: float = 0.9,
) -> CloudRecognitionCandidate:
    merged_alternatives = (primary_text, *alternatives)
    return CloudRecognitionCandidate(
        provider_source="cloud_primary",
        status="recognized",
        recognition_path="local_first",
        primary_transcript=primary_text,
        confidence_available=True,
        confidence_score=confidence,
        alternative_transcripts=merged_alternatives,
        selected_language=selected_language,
        detected_language=detected_language or selected_language,
        latency_ms=80,
        failure_reason_code=None,
    )


def _count_successes(listener: VoiceListener, fixtures: tuple[tuple[str, str], ...]) -> int:
    successes = 0
    for language_code, _expected in fixtures:
        candidates = listener._recognize_audio_candidates(
            _Audio(),
            language_code=language_code,
            for_command=True,
            usage_mode="command",
            recognition_path="local_first",
            closed_vocabulary_id=None,
            closed_vocabulary_choices=None,
        )
        successes += int(bool(candidates))
    return successes


@pytest.fixture()
def clear_cloud_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "EGB_STT_CLOUD_PRIMARY_ENABLED",
        "EGB_STT_STRICT_VOSK_FALLBACK_ENABLED",
        "EGB_STT_ENABLE_SPHINX_COMPAT",
    ):
        monkeypatch.delenv(name, raising=False)


def test_cloud_primary_command_candidates_preserve_metadata_and_alternatives(
    clear_cloud_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EGB_STT_CLOUD_PRIMARY_ENABLED", "1")
    monkeypatch.setenv("EGB_STT_STRICT_VOSK_FALLBACK_ENABLED", "0")
    listener = VoiceListener(default_language="en-US")

    monkeypatch.setattr(
        listener,
        "_recognize_cloud_candidate",
        lambda **_kwargs: _recognized_candidate(
            "read text",
            selected_language="en-US",
            detected_language="ar-EG",
            alternatives=("reed text",),
            confidence=0.93,
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
    assert len(candidates) == 2
    assert candidates[0][0] == "read text"
    assert candidates[0][2] == "cloud_primary"
    assert candidates[1][0] == "reed text"
    assert candidates[0][3]["recognition_source"] == "cloud_primary"
    assert candidates[0][3]["selected_language"] == "en-US"
    assert candidates[0][3]["detected_language"] == "ar-EG"
    assert candidates[0][3]["failure_reason_code"] is None


def test_disabled_cloud_rollout_preserves_local_candidate_path(
    clear_cloud_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EGB_STT_CLOUD_PRIMARY_ENABLED", "0")
    listener = VoiceListener(default_language="en-US")

    monkeypatch.setattr(
        listener,
        "_recognize_cloud_candidate",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("cloud path must stay disabled")),
    )
    monkeypatch.setattr(
        listener,
        "_recognize_vosk_candidates",
        lambda *_args, **_kwargs: [("start obstacle detection", 0.81)],
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
    assert candidates
    assert candidates[0][0] == "start obstacle detection"
    assert candidates[0][2] == "local_vosk"


def test_cloud_primary_fixtures_outperform_local_baseline_for_arabic_and_bilingual(
    clear_cloud_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EGB_STT_CLOUD_PRIMARY_ENABLED", "0")
    local_listener = VoiceListener(default_language="en-US")
    local_outputs = iter(
        [
            [("start obstacle detection", 0.84)],
            [],
            [],
            [],
        ]
    )
    monkeypatch.setattr(local_listener, "_recognize_vosk_candidates", lambda *_args, **_kwargs: next(local_outputs))
    local_successes = _count_successes(local_listener, _ARABIC_BILINGUAL_BASELINE_FIXTURES)

    monkeypatch.setenv("EGB_STT_CLOUD_PRIMARY_ENABLED", "1")
    monkeypatch.setenv("EGB_STT_STRICT_VOSK_FALLBACK_ENABLED", "0")
    cloud_listener = VoiceListener(default_language="en-US")
    cloud_outputs = iter(
        [
            _recognized_candidate("start obstacle detection", selected_language="en-US"),
            _recognized_candidate(_AR_READ_TEXT, selected_language="ar-EG"),
            _recognized_candidate(_AR_OBSTACLE, selected_language="ar-EG"),
            _recognized_candidate("help me", selected_language="en-US"),
        ]
    )
    monkeypatch.setattr(cloud_listener, "_recognize_cloud_candidate", lambda **_kwargs: next(cloud_outputs))
    cloud_successes = _count_successes(cloud_listener, _ARABIC_BILINGUAL_BASELINE_FIXTURES)

    assert cloud_successes > local_successes


def test_cloud_primary_reduces_common_command_fallback_to_retry_baseline(
    clear_cloud_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EGB_STT_CLOUD_PRIMARY_ENABLED", "0")
    local_listener = VoiceListener(default_language="en-US")
    local_outputs = iter(
        [
            [("start obstacle detection", 0.84)],
            [],
            [],
        ]
    )
    monkeypatch.setattr(local_listener, "_recognize_vosk_candidates", lambda *_args, **_kwargs: next(local_outputs))
    local_retry_like = 0
    for phrase in _COMMON_COMMAND_FIXTURES:
        candidates = local_listener._recognize_audio_candidates(
            _Audio(),
            language_code="en-US",
            for_command=True,
            usage_mode="command",
            recognition_path="local_first",
            closed_vocabulary_id=None,
            closed_vocabulary_choices=None,
        )
        local_retry_like += int(not candidates or candidates[0][0] != phrase)

    monkeypatch.setenv("EGB_STT_CLOUD_PRIMARY_ENABLED", "1")
    monkeypatch.setenv("EGB_STT_STRICT_VOSK_FALLBACK_ENABLED", "0")
    cloud_listener = VoiceListener(default_language="en-US")
    cloud_outputs = iter(
        [_recognized_candidate(phrase, selected_language="en-US") for phrase in _COMMON_COMMAND_FIXTURES]
    )
    monkeypatch.setattr(cloud_listener, "_recognize_cloud_candidate", lambda **_kwargs: next(cloud_outputs))
    cloud_retry_like = 0
    for phrase in _COMMON_COMMAND_FIXTURES:
        candidates = cloud_listener._recognize_audio_candidates(
            _Audio(),
            language_code="en-US",
            for_command=True,
            usage_mode="command",
            recognition_path="local_first",
            closed_vocabulary_id=None,
            closed_vocabulary_choices=None,
        )
        cloud_retry_like += int(not candidates or candidates[0][0] != phrase)

    assert cloud_retry_like < local_retry_like


def test_recognize_candidates_prefers_active_language_when_bilingual_results_are_close(
    clear_cloud_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listener = VoiceListener(default_language="ar-EG")

    def _fake_candidates(_audio, *, language_code: str, **_kwargs):
        if language_code == "ar-EG":
            return [
                ("\u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0646\u0635\u0648\u0635", 0.81, "cloud_primary", {
                    "recognition_source": "cloud_primary",
                    "selected_language": "ar-EG",
                    "detected_language": "ar-EG",
                    "failure_reason_code": None,
                })
            ]
        return [
            ("does it start off", 0.93, "cloud_primary", {
                "recognition_source": "cloud_primary",
                "selected_language": "en-US",
                "detected_language": "en-US",
                "failure_reason_code": None,
            })
        ]

    monkeypatch.setattr(listener, "_recognize_audio_candidates", _fake_candidates)
    top_text, top_language, alternatives, top_confidence, metadata = listener._recognize_candidates(
        _Audio(),
        languages=["ar-EG", "en-US"],
        for_command=True,
        usage_mode="command",
        recognition_path="local_first",
    )

    assert top_text == "\u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0646\u0635\u0648\u0635"
    assert top_language == "ar-EG"
    assert alternatives[0] == "\u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0646\u0635\u0648\u0635"
    assert top_confidence == pytest.approx(0.81)
    assert metadata["selected_language"] == "ar-EG"
