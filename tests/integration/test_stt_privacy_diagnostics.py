"""Integration checks for field-safe STT diagnostics and privacy boundaries."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.command_models import CommandRecognitionResult, build_command_fallback_decision
from core.runtime_diagnostics import attach_runtime_diagnostic_fields, attach_wake_outcome_fields
from core.stt import VoiceListener


def test_runtime_diagnostics_redact_raw_user_content() -> None:
    payload = {
        "provider_source": "cloud_primary",
        "raw_utterance": "user said hello",
        "nested": {"normalized_text": "hello"},
    }
    diagnostic = attach_runtime_diagnostic_fields(
        payload,
        session_or_run_id="session-1",
        event_category="stt_recognition",
        status_or_decision="failed",
        reason_code="cloud_network_timeout",
        provider_id="legacy",
        provider_availability="ready",
        degraded_mode=False,
        degraded_reason=None,
        raw_user_content_present=False,
    )
    assert "raw_utterance" not in diagnostic
    assert "normalized_text" not in diagnostic["nested"]
    assert diagnostic["field_safe"] is True
    assert diagnostic["raw_user_content_present"] is False


def test_recognition_configuration_snapshot_never_contains_credential_material(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    creds = tmp_path / "gcp.json"
    creds.write_text('{"type":"service_account"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds))
    listener = VoiceListener(default_language="en-US")
    snapshot = listener.recognition_configuration_snapshot()
    serialized = str(snapshot)
    assert "GOOGLE_APPLICATION_CREDENTIALS" not in serialized
    assert str(creds) not in serialized
    assert snapshot["credential_material_present"] is False


def test_field_safe_command_result_rejects_raw_user_content_flag() -> None:
    with pytest.raises(ValueError):
        CommandRecognitionResult(
            session_id="session-privacy",
            recognition_path="local_first",
            provider_id="legacy",
            primary_transcript="read text",
            confidence_available=False,
            confidence_score=None,
            alternative_transcripts=("read text",),
            detected_language="en-US",
            latency_ms=10,
            error_code=None,
            raw_user_content_present=True,
            field_safe=True,
        )


def test_command_fallback_decision_diagnostics_remain_field_safe() -> None:
    fallback_decision = build_command_fallback_decision(
        status_or_decision="fallback",
        trigger="cloud_timeout",
        recognition_source="cloud_primary",
        fallback_enabled=True,
        fallback_attempted=True,
        fallback_mode="command_inventory",
        reason_code="cloud_network_timeout",
        confidence_band="missing_confidence",
        selected_language="en-US",
        detected_language=None,
        latency_ms=3000,
    )
    diagnostic = attach_runtime_diagnostic_fields(
        fallback_decision,
        session_or_run_id="session-command-fallback",
        event_category="command_recognition",
        status_or_decision="fallback",
        reason_code="cloud_network_timeout",
        provider_id="legacy",
        provider_availability="ready",
        degraded_mode=False,
        degraded_reason=None,
        raw_user_content_present=False,
    )
    assert diagnostic["trigger"] == "cloud_timeout"
    assert diagnostic["recognition_source"] == "cloud_primary"
    assert diagnostic["reason_code"] == "cloud_network_timeout"
    assert diagnostic["field_safe"] is True
    assert diagnostic["raw_user_content_present"] is False


def test_fallback_decision_supports_strict_no_match_and_cloud_unavailable_sources() -> None:
    no_match = build_command_fallback_decision(
        status_or_decision="no_usable_transcript",
        trigger="strict_grammar_no_match",
        recognition_source="rescue_strict_vosk",
        fallback_enabled=True,
        fallback_attempted=True,
        fallback_mode="command_inventory",
        reason_code="strict_grammar_no_match",
        confidence_band="low",
        selected_language="ar-EG",
        detected_language="ar-EG",
        latency_ms=150,
    )
    cloud_unavailable = build_command_fallback_decision(
        status_or_decision="no_usable_transcript",
        trigger="cloud_unavailable",
        recognition_source="cloud_unavailable",
        fallback_enabled=False,
        fallback_attempted=False,
        fallback_mode=None,
        reason_code="cloud_service_unavailable",
        confidence_band="missing_confidence",
        selected_language="en-US",
        detected_language=None,
        latency_ms=2100,
    )
    assert no_match["recognition_source"] == "rescue_strict_vosk"
    assert no_match["reason_code"] == "strict_grammar_no_match"
    assert cloud_unavailable["recognition_source"] == "cloud_unavailable"
    assert cloud_unavailable["reason_code"] == "cloud_service_unavailable"
    assert cloud_unavailable["field_safe"] is True


def test_wake_outcome_diagnostics_for_noncanonical_rejected_are_field_safe() -> None:
    diagnostic = attach_wake_outcome_fields(
        {
            "trigger": "wake_policy",
            "status": "wake_rejected",
            "error_code": "wake_phrase_not_approved",
        },
        session_or_run_id="session-wake-reject",
        status="wake_rejected",
        source_classification="noncanonical_rejected",
        reason_code="wake_phrase_not_approved",
        next_state="standby",
    )
    assert diagnostic["status"] == "wake_rejected"
    assert diagnostic["source_classification"] == "noncanonical_rejected"
    assert diagnostic["field_safe"] is True
    assert diagnostic["raw_user_content_present"] is False


def test_wake_outcome_diagnostics_for_wake_missed_are_field_safe() -> None:
    diagnostic = attach_wake_outcome_fields(
        {
            "trigger": "wake_policy",
            "status": "wake_missed",
            "payload": {"wake_miss_streak": 50},
        },
        session_or_run_id="session-wake-missed",
        status="wake_missed",
        source_classification="wake_strict_vosk_fallback",
        reason_code="strict_grammar_no_match",
        next_state="standby",
    )
    assert diagnostic["status"] == "wake_missed"
    assert diagnostic["source_classification"] == "wake_strict_vosk_fallback"
    assert diagnostic["reason_code"] == "strict_grammar_no_match"
    assert diagnostic["field_safe"] is True
