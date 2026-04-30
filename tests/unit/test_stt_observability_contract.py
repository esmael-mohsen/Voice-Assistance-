"""Unit contract tests for STT observability events and rollups."""

from core.release_metrics import build_stt_telemetry_rollup, record_stt_observability_event
from core.release_models import SttTelemetryEventRecord


def test_stt_observability_event_contract_requires_field_safe_defaults() -> None:
    event = SttTelemetryEventRecord(
        event_id="evt-1",
        session_id="session-1",
        candidate_run_id="candidate-1",
        event_type="cloud_failure",
        source="google_cloud",
        rollout_mode="commands_low_risk",
        status="failed",
        confidence_bucket="missing",
        failure_category="cloud_timeout",
        recovery_outcome="fallback",
        latency_bucket="over_baseline",
        reason_code="cloud_timeout_strict_fallback",
    )
    payload = event.to_dict()
    assert payload["field_safe"] is True
    assert payload["raw_audio_present"] is False
    assert payload["raw_utterance_present"] is False


def test_stt_rollup_aggregates_event_and_failure_rates() -> None:
    session_id = "session-rollup"
    candidate_id = "candidate-rollup"
    record_stt_observability_event(
        event=SttTelemetryEventRecord(
            event_id="evt-1",
            session_id=session_id,
            candidate_run_id=candidate_id,
            event_type="cloud_attempt",
            source="google_cloud",
            rollout_mode="shadow",
            status="succeeded",
            confidence_bucket="high",
            failure_category="none",
            recovery_outcome="none",
            latency_bucket="within_target",
            reason_code="cloud_success",
        )
    )
    record_stt_observability_event(
        event=SttTelemetryEventRecord(
            event_id="evt-2",
            session_id=session_id,
            candidate_run_id=candidate_id,
            event_type="cloud_failure",
            source="google_cloud",
            rollout_mode="shadow",
            status="failed",
            confidence_bucket="missing",
            failure_category="cloud_timeout",
            recovery_outcome="fallback",
            latency_bucket="threshold_breach",
            reason_code="cloud_timeout_strict_fallback",
        )
    )
    rollup = build_stt_telemetry_rollup(session_id=session_id, candidate_run_id=candidate_id)
    assert rollup["event_count"] == 2
    assert rollup["cloud_failure_frequency"] == 0.5
    assert rollup["fallback_frequency"] == 0.5
    assert rollup["field_safe"] is True
