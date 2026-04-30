"""Integration tests for STT observability event and rollup flow."""

from core.release_metrics import (
    build_stt_telemetry_rollup,
    classify_stt_failure_category,
    classify_stt_latency_bucket,
    classify_stt_recovery_outcome,
    get_stt_observability_events,
    record_stt_observability_event,
)
from core.release_models import SttTelemetryEventRecord


def test_stt_observability_pipeline_records_cloud_and_fallback_paths() -> None:
    session_id = "integration-session-obs"
    candidate_id = "integration-candidate-obs"

    record_stt_observability_event(
        event=SttTelemetryEventRecord(
            event_id="evt-cloud",
            session_id=session_id,
            candidate_run_id=candidate_id,
            event_type="cloud_failure",
            source="google_cloud",
            rollout_mode="commands_low_risk",
            status="failed",
            confidence_bucket="missing",
            failure_category=classify_stt_failure_category("cloud_network_timeout"),
            recovery_outcome=classify_stt_recovery_outcome("fallback"),
            latency_bucket=classify_stt_latency_bucket(latency_ms=3100),
            reason_code="cloud_network_timeout",
        )
    )
    record_stt_observability_event(
        event=SttTelemetryEventRecord(
            event_id="evt-fallback",
            session_id=session_id,
            candidate_run_id=candidate_id,
            event_type="strict_fallback",
            source="strict_vosk",
            rollout_mode="commands_low_risk",
            status="recovered",
            confidence_bucket="medium",
            failure_category="none",
            recovery_outcome="none",
            latency_bucket=classify_stt_latency_bucket(latency_ms=1450),
            reason_code="strict_vosk_success",
        )
    )

    events = get_stt_observability_events(session_id, candidate_run_id=candidate_id)
    rollup = build_stt_telemetry_rollup(session_id=session_id, candidate_run_id=candidate_id)

    assert len(events) == 2
    assert rollup["source_counts"]["google_cloud"] == 1
    assert rollup["source_counts"]["strict_vosk"] == 1
    assert rollup["cloud_failure_frequency"] == 0.5
    assert rollup["field_safe"] is True
