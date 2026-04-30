"""Unit tests for wearable offline allowlist policy behavior."""

from __future__ import annotations

from core.runtime_diagnostics import attach_runtime_diagnostic_fields
from core.speech.provider_resolver import evaluate_offline_execution_policy


def test_requires_network_without_allowlist_returns_safe_refusal() -> None:
    decision = evaluate_offline_execution_policy(
        capability_id="ocr",
        provider_id="speakkit",
        requires_network=True,
        effective_network_available=False,
        override_mode="auto",
        detected_status="offline",
        provider_availability="ready",
        offline_allowlist={"system_status"},
    )
    assert decision.decision == "safe_refusal"
    assert decision.offline_allowlisted is False
    assert decision.error_code == "offline_not_allowlisted"


def test_allowlisted_offline_capability_uses_on_device_fallback() -> None:
    decision = evaluate_offline_execution_policy(
        capability_id="system_status",
        provider_id="speakkit",
        requires_network=True,
        effective_network_available=False,
        override_mode="auto",
        detected_status="offline",
        provider_availability="ready",
        offline_allowlist={"system_status"},
    )
    assert decision.decision == "on_device_fallback"
    assert decision.offline_allowlisted is True
    assert decision.error_code == "offline_allowlisted_fallback"


def test_network_optional_capability_can_execute_while_offline() -> None:
    decision = evaluate_offline_execution_policy(
        capability_id="obstacle_detection",
        provider_id="legacy",
        requires_network=False,
        effective_network_available=False,
        override_mode="force_offline",
        detected_status="offline",
        provider_availability="ready",
        offline_allowlist=set(),
    )
    assert decision.decision == "allow_execution"
    assert decision.error_code is None


def test_offline_policy_diagnostic_payload_is_field_safe_by_default() -> None:
    decision = evaluate_offline_execution_policy(
        capability_id="ocr",
        provider_id="speakkit",
        requires_network=True,
        effective_network_available=False,
        override_mode="auto",
        detected_status="offline",
        provider_availability="ready",
        offline_allowlist={"system_status"},
    )

    payload = attach_runtime_diagnostic_fields(
        decision.to_dict(),
        session_or_run_id="session-offline",
        event_category="offline_policy",
        status_or_decision=decision.decision,
        reason_code=decision.error_code,
        provider_id=decision.provider_id,
        provider_availability=decision.provider_availability,
        degraded_mode=False,
        degraded_reason=None,
        next_state="listening",
        user_outcome=decision.spoken_text,
    )

    assert payload["event_category"] == "offline_policy"
    assert payload["field_safe"] is True
    assert payload["raw_user_content_present"] is False
    assert payload["provider_context"]["provider_id"] == "speakkit"
