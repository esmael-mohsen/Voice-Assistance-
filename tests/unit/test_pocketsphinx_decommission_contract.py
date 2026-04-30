"""Unit tests for PocketSphinx decommission evidence contract."""

from core.release_models import PocketSphinxDecommissionEvidence
from core.stt import VoiceListener


def test_pocketsphinx_decommission_contract_excludes_production_baseline() -> None:
    evidence = PocketSphinxDecommissionEvidence(
        candidate_run_id="candidate-1",
        default_candidate_count=0,
        default_invocation_count=0,
        compatibility_flag_status="disabled_by_default",
        accuracy_baseline_includes_sphinx=False,
        compatibility_tests_present=True,
        documentation_status="updated",
    )
    payload = evidence.to_dict()
    assert payload["default_candidate_count"] == 0
    assert payload["default_invocation_count"] == 0
    assert payload["accuracy_baseline_includes_sphinx"] is False


def test_voice_listener_reports_zero_default_pocketsphinx_usage() -> None:
    listener = VoiceListener(default_language="en-US")
    usage = listener.pocketsphinx_usage_snapshot()
    assert usage["default_candidate_count"] == 0
    assert usage["default_invocation_count"] == 0
