"""Integration tests for primary journey release validation."""

from __future__ import annotations

from core.release_artifacts import persist_pilot_voice_ux_summary
from core.release_journey_checks import run_journey_validation
from core.release_metrics import build_pilot_voice_ux_summary
from core.release_models import PilotVoiceUXSummary


def test_journey_validation_passes_when_all_journeys_succeed() -> None:
    gate_result = run_journey_validation(
        journey_results={
            "startup_to_ready": True,
            "wake_to_command": True,
            "command_to_spoken_response": True,
        }
    )

    assert gate_result.status == "passed"


def test_journey_validation_fails_when_any_critical_journey_fails() -> None:
    gate_result = run_journey_validation(
        journey_results={
            "startup_to_ready": True,
            "wake_to_command": False,
            "command_to_spoken_response": True,
        }
    )

    assert gate_result.status == "failed"
    assert gate_result.failure_code == "journey_regression_detected"


def test_release_journey_validation_persists_field_safe_pilot_voice_ux_summary(tmp_path) -> None:
    payload = build_pilot_voice_ux_summary(
        run_id="pilot-ux-test-01",
        scenario_label="mixed-language-onboarding",
        journey_type="onboarding",
        completion_status="safe_default_continuation",
        retries_used=2,
        accepted_barge_in_count=1,
        prompt_echo_suppression_count=1,
        out_of_domain_rejection_count=1,
        fallback_or_exit_reason="retry_exhausted_keep_default",
        artifact_path="artifacts/pilot-ux-test-01/voice-ux-summary.json",
    )
    summary = PilotVoiceUXSummary(**payload)
    entry = persist_pilot_voice_ux_summary(storage_root=tmp_path, summary=summary)

    assert entry.kind == "pilot_voice_ux_summary"
    assert entry.path.endswith("voice-ux-summary.json")
    assert summary.raw_utterance_present is False
