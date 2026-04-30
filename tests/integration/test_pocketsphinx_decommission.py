"""Integration tests for default PocketSphinx exclusion in release gates."""

from core.release_gates import evaluate_rollout_mode_state, evaluate_stt_rollout_release_gate
from core.stt import VoiceListener


def test_release_gate_blocks_when_default_pocketsphinx_usage_is_non_zero() -> None:
    state = evaluate_rollout_mode_state(
        requested_mode="full_cloud_primary",
        effective_mode="full_cloud_primary",
        rollback_override_active=False,
    )
    gate = evaluate_stt_rollout_release_gate(
        candidate_run_id="candidate-sphinx-1",
        rollout_state=state,
        cloud_configuration_ok=True,
        strict_fallback_ok=True,
        wake_fallback_ok=True,
        protected_command_ok=True,
        bilingual_regression_ok=True,
        bounded_recovery_ok=True,
        pi4_qualification_ok=True,
        pocketsphinx_default_candidate_count=0,
        pocketsphinx_default_invocation_count=1,
    )
    assert gate.gate_status == "blocked"
    assert "default_pocketsphinx_invocations_detected" in gate.blocked_reasons


def test_listener_snapshot_marks_sphinx_compatibility_disabled_by_default() -> None:
    listener = VoiceListener(default_language="en-US")
    usage = listener.pocketsphinx_usage_snapshot()
    assert usage["compatibility_flag_status"] in {"enabled", "disabled_by_default"}
