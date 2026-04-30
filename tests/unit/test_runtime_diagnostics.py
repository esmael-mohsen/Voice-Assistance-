"""Unit tests for STT observability diagnostic helpers."""

from core.runtime_diagnostics import (
    attach_rollout_mode_fields,
    attach_stt_failure_scenario_fields,
    attach_stt_observability_fields,
)


def test_attach_stt_observability_fields_remains_field_safe() -> None:
    payload = attach_stt_observability_fields(
        {"raw_utterance": "hello"},
        session_id="session-1",
        candidate_run_id="run-1",
        event_type="cloud_failure",
        source="google_cloud",
        rollout_mode="shadow",
        status="failed",
        confidence_bucket="missing",
        failure_category="cloud_timeout",
        recovery_outcome="fallback",
        latency_bucket="over_baseline",
        reason_code="cloud_timeout_strict_fallback",
    )
    assert "raw_utterance" not in payload
    assert payload["field_safe"] is True
    assert payload["raw_audio_present"] is False
    assert payload["raw_utterance_present"] is False


def test_attach_stt_failure_scenario_fields_is_crash_free_by_default() -> None:
    payload = attach_stt_failure_scenario_fields(
        {},
        scenario_id="scenario-1",
        failure_category="language_mismatch",
        source="google_cloud",
        rollout_mode="commands_low_risk",
        bounded_outcome="retry",
        diagnostic_reason_code="language_mismatch_recovery",
        spoken_guidance_surface="runtime.command.retry",
    )
    assert payload["crash_free"] is True
    assert payload["field_safe_metadata"]["raw_audio_present"] is False
    assert payload["field_safe_metadata"]["raw_utterance_present"] is False


def test_attach_rollout_mode_fields_records_override_state() -> None:
    payload = attach_rollout_mode_fields(
        {},
        requested_mode="full_cloud_primary",
        effective_mode="rollback",
        rollback_override_active=True,
        rollback_reason_code="field_validation_incomplete",
    )
    assert payload["requested_mode"] == "full_cloud_primary"
    assert payload["effective_mode"] == "rollback"
    assert payload["rollback_override_active"] is True
