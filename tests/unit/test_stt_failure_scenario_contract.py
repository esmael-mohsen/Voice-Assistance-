"""Unit tests for STT failure scenario contract and taxonomy."""

from core.release_metrics import (
    classify_stt_failure_category,
    classify_stt_recovery_outcome,
)
from core.release_models import SttFailureScenarioResult


def test_stt_failure_category_mapping_covers_key_failure_families() -> None:
    assert classify_stt_failure_category("cloud_network_timeout") == "network"
    assert classify_stt_failure_category("cloud_credentials_missing") == "credentials"
    assert classify_stt_failure_category("cloud_quota_error") == "quota_or_rate"
    assert classify_stt_failure_category("strict_vosk_unavailable") == "fallback_missing"
    assert classify_stt_failure_category("language_mismatch_recovery") == "language_mismatch"


def test_stt_failure_scenario_result_requires_bounded_outcome() -> None:
    result = SttFailureScenarioResult(
        scenario_id="scenario-1",
        failure_category="cloud_timeout",
        source="google_cloud",
        rollout_mode="commands_low_risk",
        bounded_outcome=classify_stt_recovery_outcome("fallback"),
        crash_free=True,
        spoken_guidance_surface="runtime.command.fallback",
        diagnostic_reason_code="cloud_timeout_strict_fallback",
        field_safe_metadata={
            "raw_audio_present": False,
            "raw_utterance_present": False,
        },
    )
    payload = result.to_dict()
    assert payload["bounded_outcome"] == "fallback"
    assert payload["crash_free"] is True
