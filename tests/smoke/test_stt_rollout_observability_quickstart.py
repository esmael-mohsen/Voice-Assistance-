"""Smoke check for Phase 21 STT observability and rollout gates."""

from core.release_gates import evaluate_rollout_mode_state, evaluate_stt_rollout_release_gate
from core.release_metrics import build_stt_telemetry_rollup, record_stt_observability_event
from core.release_models import SttTelemetryEventRecord


def test_quickstart_smoke_for_stt_rollout_observability() -> None:
    session_id = "smoke-session-1"
    candidate_id = "smoke-candidate-1"
    record_stt_observability_event(
        event=SttTelemetryEventRecord(
            event_id="smoke-event-1",
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
    rollup = build_stt_telemetry_rollup(session_id=session_id, candidate_run_id=candidate_id)
    state = evaluate_rollout_mode_state(
        requested_mode="shadow",
        effective_mode="shadow",
        rollback_override_active=False,
        user_visible_behavior_changed=False,
    )
    gate = evaluate_stt_rollout_release_gate(
        candidate_run_id=candidate_id,
        rollout_state=state,
        cloud_configuration_ok=True,
        strict_fallback_ok=True,
        wake_fallback_ok=True,
        protected_command_ok=True,
        bilingual_regression_ok=True,
        bounded_recovery_ok=True,
        pi4_qualification_ok=True,
        pocketsphinx_default_candidate_count=0,
        pocketsphinx_default_invocation_count=0,
    )
    assert rollup["event_count"] == 1
    assert gate.gate_status == "approved"
