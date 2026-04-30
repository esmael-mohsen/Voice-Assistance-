"""Integration tests for STT rollout release-gate blocking semantics."""

from core.release_gates import evaluate_rollout_mode_state, evaluate_stt_rollout_release_gate


def test_rollout_release_gate_approves_when_all_inputs_are_safe() -> None:
    state = evaluate_rollout_mode_state(
        requested_mode="wake_only",
        effective_mode="wake_only",
        rollback_override_active=False,
    )
    gate = evaluate_stt_rollout_release_gate(
        candidate_run_id="candidate-safe",
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
    assert gate.gate_status == "approved"
    assert gate.approved_for_pilot is True
    assert gate.blocked_reasons == []


def test_rollout_release_gate_blocks_for_pocketsphinx_default_usage() -> None:
    state = evaluate_rollout_mode_state(
        requested_mode="full_cloud_primary",
        effective_mode="full_cloud_primary",
        rollback_override_active=False,
    )
    gate = evaluate_stt_rollout_release_gate(
        candidate_run_id="candidate-sphinx-regression",
        rollout_state=state,
        cloud_configuration_ok=True,
        strict_fallback_ok=True,
        wake_fallback_ok=True,
        protected_command_ok=True,
        bilingual_regression_ok=True,
        bounded_recovery_ok=True,
        pi4_qualification_ok=True,
        pocketsphinx_default_candidate_count=1,
        pocketsphinx_default_invocation_count=0,
    )
    assert gate.gate_status == "blocked"
    assert "default_pocketsphinx_candidates_detected" in gate.blocked_reasons
