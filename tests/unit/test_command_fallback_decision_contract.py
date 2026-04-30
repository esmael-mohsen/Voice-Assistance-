"""Contract tests for command fallback decision diagnostics."""

from __future__ import annotations

from core.command_models import build_command_fallback_decision


def test_fallback_decision_shape_is_field_safe_and_contract_aligned() -> None:
    payload = build_command_fallback_decision(
        status_or_decision="fallback",
        trigger="cloud_timeout",
        recognition_source="cloud_primary",
        fallback_enabled=True,
        fallback_attempted=True,
        fallback_mode="command_inventory",
        reason_code="cloud_network_timeout",
        confidence_band="missing_confidence",
        selected_language="en-US",
        detected_language=None,
        latency_ms=3000,
    )
    assert payload["status_or_decision"] == "fallback"
    assert payload["trigger"] == "cloud_timeout"
    assert payload["recognition_source"] == "cloud_primary"
    assert payload["fallback_enabled"] is True
    assert payload["fallback_attempted"] is True
    assert payload["fallback_mode"] == "command_inventory"
    assert payload["reason_code"] == "cloud_network_timeout"
    assert payload["confidence_band"] == "missing_confidence"
    assert payload["field_safe"] is True
    assert payload["raw_user_content_present"] is False


def test_fallback_decision_normalizes_unknown_source_and_band() -> None:
    payload = build_command_fallback_decision(
        status_or_decision="no_usable_transcript",
        trigger="cloud_unavailable",
        recognition_source="not_supported_source",
        fallback_enabled=False,
        fallback_attempted=False,
        fallback_mode=None,
        reason_code="cloud_service_unavailable",
        confidence_band="not-a-band",
        selected_language="ar-EG",
        detected_language="ar-EG",
        latency_ms=-20,
    )
    assert payload["status_or_decision"] == "no_usable_transcript"
    assert payload["recognition_source"] == "legacy_local"
    assert payload["confidence_band"] == "missing_confidence"
    assert payload["latency_ms"] == 0
