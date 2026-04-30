"""Smoke validations for Phase 14 audio front-end quickstart journeys."""

from __future__ import annotations

from core.command_models import AudioCaptureAttempt, CommandRecognitionResult
from core.command_post_processing import process_command_transcript
from core.release_metrics import record_audio_qualification_run


def test_smoke_capture_metadata_includes_profile_and_endpoint_hints() -> None:
    capture = AudioCaptureAttempt(
        capture_attempt_id="cap-smoke-1",
        session_id="smoke-session-1",
        profile_id="command.default",
        attempt_index=0,
        started_at_ms=0,
        ended_at_ms=1200,
        raw_duration_ms=1200,
        processed_duration_ms=1180,
        utterance_duration_ms=900,
        clipping_start_suspected=False,
        clipping_end_suspected=True,
        endpoint_quality_hints=("low_trailing_silence",),
        relisten_triggered=False,
    )
    recognition = CommandRecognitionResult(
        session_id="smoke-session-1",
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="start obstacle detection",
        confidence_available=True,
        confidence_score=0.91,
        alternative_transcripts=("start obstacle detection",),
        detected_language="en-US",
        profile_id="command.default",
        capture_attempt_id=capture.capture_attempt_id,
        capture_attempt=capture,
        endpoint_quality_hints=capture.endpoint_quality_hints,
        latency_ms=44,
        error_code=None,
    )
    assert recognition.capture_attempt_id == "cap-smoke-1"
    assert "low_trailing_silence" in recognition.endpoint_quality_hints


def test_smoke_local_first_then_rescue_path_remains_parser_safe() -> None:
    local_post = process_command_transcript("start obsticle maybe")
    rescue_post = process_command_transcript("start obstacle detection")
    assert local_post.canonical_command_text
    assert rescue_post.canonical_command_text == "start obstacle detection"
    assert rescue_post.post_processing_status in {"normalized", "unchanged"}


def test_smoke_qualification_evidence_records_profile_and_demotion_flags() -> None:
    payload = record_audio_qualification_run(
        session_id="smoke-session-3",
        qualification_profile_id="simplified",
        capture_profile_id="command.default",
        recognition_path="local_first",
        capture_complete=True,
        latency_ms=2100,
        accuracy=0.96,
        demoted_enhancements=["rescue_recognition"],
    )
    assert payload["qualification_profile_id"] == "simplified"
    assert payload["demoted_enhancements"] == ["rescue_recognition"]
    assert payload["field_safe"] is True

