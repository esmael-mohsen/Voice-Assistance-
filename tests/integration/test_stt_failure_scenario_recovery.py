"""Integration tests for bounded STT failure recovery recording."""

from core.release_metrics import (
    build_failure_scenario_from_event,
    record_stt_failure_scenario_result,
    record_stt_observability_event,
)
from core.release_models import SttTelemetryEventRecord


def test_failure_scenario_recovery_is_bounded_and_crash_free() -> None:
    event = SttTelemetryEventRecord(
        event_id="evt-failure-1",
        session_id="session-failure-1",
        candidate_run_id="candidate-failure-1",
        event_type="cloud_failure",
        source="google_cloud",
        rollout_mode="commands_low_risk",
        status="failed",
        confidence_bucket="missing",
        failure_category="cloud_timeout",
        recovery_outcome="fallback",
        latency_bucket="threshold_breach",
        reason_code="cloud_timeout_strict_fallback",
    )
    record_stt_observability_event(event=event)
    scenario = build_failure_scenario_from_event(
        event=event,
        spoken_guidance_surface="runtime.command.fallback",
    )
    persisted = record_stt_failure_scenario_result(result=scenario, session_id="session-failure-1")
    assert persisted["bounded_outcome"] in {"fallback", "retry", "safe_refusal", "standby"}
    assert persisted["crash_free"] is True
    assert persisted["field_safe_metadata"]["raw_audio_present"] is False
