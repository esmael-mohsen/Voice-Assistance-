"""Command dispatcher converts parser and resolver output into runtime contract."""

from __future__ import annotations

import logging
import time
from typing import Any

from core import parser, resolver
from core.command_models import CommandExecutionResult, CommandResolution

logger = logging.getLogger(__name__)


def _status_from_resolution(validation_status: str) -> str:
    if validation_status == "ready":
        return "success"
    return validation_status


def _build_payload(resolution: CommandResolution) -> dict[str, Any] | None:
    payload: dict[str, Any] = {}
    if resolution.params:
        payload["params"] = resolution.params
    if resolution.controller_result is not None:
        payload["controller_result"] = resolution.controller_result
        if isinstance(resolution.controller_result, dict):
            capability_id = resolution.controller_result.get("capability_id")
            if capability_id:
                payload["capability_id"] = capability_id
            if "used_fallback" in resolution.controller_result:
                payload["used_fallback"] = bool(resolution.controller_result.get("used_fallback"))
    return payload or None


def _build_execution_result(
    *,
    resolution: CommandResolution,
    parse_metadata: dict[str, Any] | None = None,
) -> CommandExecutionResult:
    metadata = dict(parse_metadata or {})
    metadata.update(resolution.metadata)
    metadata["route_target"] = resolution.route_target
    metadata["used_session_context"] = bool(resolution.used_session_context)

    return CommandExecutionResult(
        intent_id=resolution.intent_id,
        category=resolution.category,
        status=_status_from_resolution(resolution.validation_status),
        spoken_text=resolution.spoken_text,
        payload=_build_payload(resolution),
        error_code=resolution.error_code,
        metadata=metadata,
    )


def dispatch(
    text_input: str,
    *,
    canonical_command_text: str | None = None,
    recognition_metadata: dict[str, Any] | None = None,
    runtime_context: dict[str, Any] | None = None,
) -> CommandExecutionResult:
    started_at = time.perf_counter()
    parser_input = canonical_command_text if canonical_command_text is not None else text_input
    parsed = parser.parse_command(
        text_input,
        canonical_command_text=parser_input,
        recognition_metadata=recognition_metadata,
    )
    parse_metadata = {
        "score": parsed.score,
        "threshold": parsed.threshold,
        "matched_keyword": parsed.matched_keyword,
        "risk_level": parsed.risk_level,
        "accepted": parsed.accepted,
        "canonical_command_text": parser_input,
        "raw_command_text": text_input,
    }
    if recognition_metadata:
        parse_metadata["recognition"] = dict(recognition_metadata)

    if parsed.accepted:
        logger.info(
            "[DISPATCHER] Parsed intent '%s' score=%.2f threshold=%.2f",
            parsed.intent_id,
            parsed.score,
            parsed.threshold,
        )
    else:
        logger.warning(
            "[DISPATCHER] Rejected intent candidate '%s' reason=%s score=%.2f threshold=%.2f",
            parsed.intent_id,
            parsed.rejection_reason,
            parsed.score,
            parsed.threshold,
        )

    resolution = resolver.resolve_command(
        parsed_intent=parsed,
        command_text=parser_input,
        metadata=parse_metadata,
        runtime_context=runtime_context,
    )
    result = _build_execution_result(resolution=resolution, parse_metadata=parse_metadata)
    dispatch_duration_ms = int((time.perf_counter() - started_at) * 1000)
    result.metadata["dispatch_duration_ms"] = dispatch_duration_ms
    logger.info(
        "[DISPATCHER] Result status=%s intent=%s error=%s",
        result.status,
        result.intent_id,
        result.error_code,
    )
    logger.info(
        "[RELEASE_GATE] dispatch status=%s intent=%s duration_ms=%s",
        result.status,
        result.intent_id,
        dispatch_duration_ms,
    )
    return result
