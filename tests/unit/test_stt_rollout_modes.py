"""Unit tests for rollout-mode ordering and STT release-gate contracts."""

from core.release_gates import (
    evaluate_rollout_mode_state,
    evaluate_stt_rollout_release_gate,
)


def test_rollout_mode_state_supports_rollback_precedence() -> None:
    state = evaluate_rollout_mode_state(
        requested_mode="commands_low_risk",
        effective_mode="rollback",
        rollback_override_active=True,
        rollback_reason_code="field_validation_incomplete",
        field_validation_complete=False,
    )
    payload = state.to_dict()
    assert payload["effective_mode"] == "rollback"
    assert payload["rollback_override_active"] is True


def test_stt_release_gate_blocks_when_safety_gates_fail() -> None:
    state = evaluate_rollout_mode_state(
        requested_mode="commands_low_risk",
        effective_mode="commands_low_risk",
        rollback_override_active=False,
    )
    gate = evaluate_stt_rollout_release_gate(
        candidate_run_id="candidate-1",
        rollout_state=state,
        cloud_configuration_ok=True,
        strict_fallback_ok=False,
        wake_fallback_ok=True,
        protected_command_ok=True,
        bilingual_regression_ok=False,
        bounded_recovery_ok=True,
        pi4_qualification_ok=True,
        pocketsphinx_default_candidate_count=0,
        pocketsphinx_default_invocation_count=0,
    )
    assert gate.gate_status == "blocked"
    assert "missing_strict_fallback" in gate.blocked_reasons
    assert "bilingual_regression" in gate.blocked_reasons
