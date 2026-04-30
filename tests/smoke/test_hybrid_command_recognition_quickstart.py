"""Smoke coverage for Phase 13 hybrid command-recognition quickstart paths."""

from core import parser
from core.command_models import (
    CommandRecognitionResult,
    ConfidenceDecisionPolicy,
    RecognitionTelemetrySample,
)
from core.command_post_processing import process_command_transcript


def test_smoke_local_first_high_confidence_path_executes() -> None:
    recognition = CommandRecognitionResult(
        session_id="smoke-1",
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="start obstacle detection",
        confidence_score=0.95,
        confidence_available=True,
        alternative_transcripts=("start obstacle detection",),
        detected_language="en-US",
        latency_ms=12,
        error_code=None,
    )
    parsed = parser.parse_command("start obstacle detection")
    post = process_command_transcript(recognition.primary_transcript)
    policy = ConfidenceDecisionPolicy()
    band = "high" if recognition.confidence_score >= policy.high_confidence_threshold else "medium"
    assert parsed.accepted is True
    assert post.post_processing_status in {"unchanged", "normalized"}
    assert band == "high"


def test_smoke_protected_command_never_executes_silently_under_uncertainty() -> None:
    parsed = parser.parse_command("stop system")
    post = process_command_transcript("stop system", alternative_transcripts=["stop system", "start system"])
    assert parsed.intent_id == "stop_system"
    assert parsed.accepted is True
    assert "conflicting_alternatives" in post.ambiguity_flags


def test_smoke_bilingual_normalization_and_metadata_safe_telemetry() -> None:
    post = process_command_transcript("reed txt بالعربي")
    telemetry = RecognitionTelemetrySample(
        session_id="smoke-2",
        event_id="event-1",
        recognition_path="rescue",
        confidence_band="medium",
        fallback_used=True,
        decision_outcome="retry",
        protected_command=False,
        latency_ms=1400,
        field_safe=True,
        raw_utterance_present=False,
    )
    assert post.canonical_command_text
    assert "mixed" in post.language_hints
    assert telemetry.to_dict()["field_safe"] is True
    assert telemetry.to_dict()["raw_utterance_present"] is False
