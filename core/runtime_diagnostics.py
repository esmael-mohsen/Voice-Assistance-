"""Helpers for building canonical field-safe runtime diagnostic payloads."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_RAW_USER_KEYS: frozenset[str] = frozenset(
    {
        "raw_utterance",
        "normalized_utterance",
        "raw_text",
        "normalized_text",
        "user_utterance",
        "raw_audio",
        "raw_audio_path",
        "transcript",
        "utterance",
    }
)


def redact_raw_user_content(value: Any) -> Any:
    """Remove raw user utterance fields while preserving machine-readable context."""
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, nested in value.items():
            if key in _RAW_USER_KEYS:
                continue
            sanitized[key] = redact_raw_user_content(nested)
        return sanitized
    if isinstance(value, list):
        return [redact_raw_user_content(item) for item in value]
    if isinstance(value, tuple):
        return [redact_raw_user_content(item) for item in value]
    return value


def attach_runtime_diagnostic_fields(
    payload: dict[str, Any],
    *,
    session_or_run_id: str,
    event_category: str,
    status_or_decision: str,
    reason_code: str | None,
    provider_id: str | None = None,
    provider_availability: str | None = None,
    degraded_mode: bool | None = None,
    degraded_reason: str | None = None,
    next_state: str | None = None,
    latency_ms: int | None = None,
    user_outcome: str | None = None,
    raw_user_content_present: bool = False,
) -> dict[str, Any]:
    diagnostic_payload = redact_raw_user_content(dict(payload))
    field_safe = not raw_user_content_present
    diagnostic_payload.update(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_or_run_id": session_or_run_id,
            "event_category": event_category,
            "status_or_decision": status_or_decision,
            "reason_code": reason_code,
            "provider_context": {
                "provider_id": provider_id,
                "provider_availability": provider_availability,
                "degraded_mode": bool(degraded_mode),
                "degraded_reason": degraded_reason,
            },
            "field_safe": field_safe,
            "raw_user_content_present": bool(raw_user_content_present),
        }
    )
    if provider_id is not None:
        diagnostic_payload.setdefault("provider_id", provider_id)
    if provider_availability is not None:
        diagnostic_payload.setdefault("provider_availability", provider_availability)
    if degraded_mode is not None:
        diagnostic_payload.setdefault("degraded_mode", bool(degraded_mode))
    if degraded_reason is not None:
        diagnostic_payload.setdefault("degraded_reason", degraded_reason)
    if next_state is not None:
        diagnostic_payload["next_state"] = next_state
    if latency_ms is not None:
        diagnostic_payload["latency_ms"] = max(0, int(latency_ms))
    if user_outcome:
        diagnostic_payload["user_outcome"] = user_outcome
    return diagnostic_payload


def attach_audio_qualification_fields(
    payload: dict[str, Any],
    *,
    qualification_profile_id: str,
    capture_profile_id: str | None = None,
    demoted_enhancements: list[str] | None = None,
) -> dict[str, Any]:
    """Attach Phase 14 qualification context without raw user audio."""
    qualified_payload = dict(payload)
    qualified_payload["qualification_profile_id"] = str(qualification_profile_id or "default")
    if capture_profile_id is not None:
        qualified_payload["capture_profile_id"] = str(capture_profile_id)
    qualified_payload["demoted_enhancements"] = list(demoted_enhancements or ())
    qualified_payload["field_safe"] = bool(qualified_payload.get("field_safe", True))
    qualified_payload["raw_user_content_present"] = False
    return qualified_payload


def attach_wake_outcome_fields(
    payload: dict[str, Any],
    *,
    session_or_run_id: str,
    status: str,
    source_classification: str | None,
    reason_code: str | None = None,
    next_state: str | None = None,
) -> dict[str, Any]:
    wake_payload = dict(payload)
    wake_payload["source_classification"] = source_classification
    wake_payload["status"] = status
    wake_payload["field_safe"] = True
    wake_payload["raw_user_content_present"] = False
    return attach_runtime_diagnostic_fields(
        wake_payload,
        session_or_run_id=session_or_run_id,
        event_category="wake_outcome",
        status_or_decision=status,
        reason_code=reason_code,
        next_state=next_state,
        raw_user_content_present=False,
    )


def attach_speech_telemetry_fields(
    payload: dict[str, Any],
    *,
    event_id: str,
    scenario_label: str,
    event_type: str,
    session_id: str,
    interaction_id: str,
    event_source: str,
    outcome_status: str,
    evidence_scope: str = "live",
    persisted_locally: bool = True,
    external_sink_status: str = "not_configured",
    latency_ms: int | None = None,
    metric_value: float | int | None = None,
) -> dict[str, Any]:
    telemetry_payload = redact_raw_user_content(dict(payload))
    telemetry_payload.update(
        {
            "event_id": event_id,
            "scenario_label": scenario_label,
            "event_type": event_type,
            "session_id": session_id,
            "interaction_id": interaction_id,
            "timestamp_ms": int(datetime.now(timezone.utc).timestamp() * 1000),
            "event_source": event_source,
            "outcome_status": outcome_status,
            "latency_ms": latency_ms,
            "metric_value": metric_value,
            "evidence_scope": evidence_scope,
            "persisted_locally": bool(persisted_locally),
            "external_sink_status": external_sink_status,
            "field_safe": True,
            "raw_user_content_present": False,
        }
    )
    return telemetry_payload


def attach_stt_observability_fields(
    payload: dict[str, Any],
    *,
    session_id: str,
    candidate_run_id: str,
    event_type: str,
    source: str,
    rollout_mode: str,
    status: str,
    confidence_bucket: str,
    failure_category: str,
    recovery_outcome: str,
    latency_bucket: str,
    reason_code: str,
) -> dict[str, Any]:
    stt_payload = redact_raw_user_content(dict(payload))
    stt_payload.update(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "candidate_run_id": candidate_run_id,
            "event_type": event_type,
            "source": source,
            "rollout_mode": rollout_mode,
            "status": status,
            "confidence_bucket": confidence_bucket,
            "failure_category": failure_category,
            "recovery_outcome": recovery_outcome,
            "latency_bucket": latency_bucket,
            "reason_code": reason_code,
            "field_safe": True,
            "raw_audio_present": False,
            "raw_utterance_present": False,
        }
    )
    return stt_payload


def attach_stt_failure_scenario_fields(
    payload: dict[str, Any],
    *,
    scenario_id: str,
    failure_category: str,
    source: str,
    rollout_mode: str,
    bounded_outcome: str,
    diagnostic_reason_code: str,
    spoken_guidance_surface: str | None = None,
) -> dict[str, Any]:
    scenario_payload = redact_raw_user_content(dict(payload))
    scenario_payload.update(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scenario_id": scenario_id,
            "failure_category": failure_category,
            "source": source,
            "rollout_mode": rollout_mode,
            "bounded_outcome": bounded_outcome,
            "crash_free": True,
            "diagnostic_reason_code": diagnostic_reason_code,
            "spoken_guidance_surface": spoken_guidance_surface,
            "field_safe_metadata": {
                "raw_audio_present": False,
                "raw_utterance_present": False,
            },
        }
    )
    return scenario_payload


def attach_rollout_mode_fields(
    payload: dict[str, Any],
    *,
    requested_mode: str,
    effective_mode: str,
    rollback_override_active: bool,
    rollback_reason_code: str | None = None,
    field_validation_complete: bool = False,
) -> dict[str, Any]:
    rollout_payload = dict(payload)
    rollout_payload.update(
        {
            "requested_mode": requested_mode,
            "effective_mode": effective_mode,
            "rollback_override_active": bool(rollback_override_active),
            "rollback_reason_code": rollback_reason_code,
            "field_validation_complete": bool(field_validation_complete),
            "field_safe": True,
            "raw_user_content_present": False,
        }
    )
    return rollout_payload
