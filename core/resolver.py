"""Command resolver routes parsed intents to controllers with safety guards."""

from __future__ import annotations

import logging
import re
from typing import Any

from controllers import capability_registry as cap_registry
from controllers import mock_controllers as mc
from core import dialog_policy
from core import parser as command_parser
from core.command_models import CommandResolution, ParsedCommandIntent, SessionCommandContext
from core.speech.provider_resolver import evaluate_offline_execution_policy
from settings.settings_manager import settings_manager

logger = logging.getLogger(__name__)

SESSION_CONTEXT = SessionCommandContext()

COMMAND_FUNCTION_MAPPING = {
    "enable_obstacle_detection": cap_registry.enable_obstacle_detection,
    "disable_obstacle_detection": cap_registry.disable_obstacle_detection,
    "recognize_face": cap_registry.recognize_face,
    "recognize_emotion": cap_registry.recognize_emotion,
    "enable_money_detection": cap_registry.enable_money_detection,
    "disable_money_detection": cap_registry.disable_money_detection,
    "enable_OCR": cap_registry.enable_OCR,
    "disable_OCR": cap_registry.disable_OCR,
    "start_system": mc.start_system,
    "stop_system": mc.stop_system,
    "get_system_status": cap_registry.get_system_status,
    "reset_settings": mc.reset_settings,
}

LANGUAGE_COMMANDS = {
    "set_language_ar": "ar-EG",
    "set_language_en": "en-US",
}

VOICE_GENDER_COMMANDS = {
    "set_voice_gender_male": "male",
    "set_voice_gender_female": "female",
}

SPEECH_SPEED_PRESETS = {"speech_speed_normal": 1.0}
SPEECH_SPEED_DELTAS = {
    "speech_speed_increase": 0.15,
    "speech_speed_decrease": -0.15,
}

PARAMETER_REQUIRED_INTENTS = {"set_language", "set_voice_gender"}
PROTECTED_INTENTS = {"stop_system", "reset_settings"}
MAX_CLARIFICATION_ATTEMPTS = 3
MAX_CONFIRMATION_RETRY_ATTEMPTS = 1
NETWORK_REQUIRED_INTENTS = {
    "enable_OCR",
    "disable_OCR",
    "enable_money_detection",
    "disable_money_detection",
    "recognize_face",
    "recognize_emotion",
    "get_system_status",
}



def get_session_context() -> SessionCommandContext:
    return SESSION_CONTEXT


def reset_session_context() -> None:
    SESSION_CONTEXT.last_face_id = None
    SESSION_CONTEXT.clear_follow_up()
    SESSION_CONTEXT.clear_confirmation()
    SESSION_CONTEXT.clear_clarification()
    cap_registry.reset_default_registry()


def _localized(ar_text: str, en_text: str) -> str:
    return settings_manager.speak_localized(ar_text, en_text)


def _critical_surface_localized(
    surface_id: str,
    *,
    format_kwargs: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    resolved = settings_manager.resolve_critical_surface(surface_id, format_kwargs=format_kwargs)
    text = str(resolved.get("text", "") or "")
    settings_manager.speak(text)
    metadata = {
        "prompt_key": resolved.get("prompt_key"),
        "surface_id": resolved.get("surface_id"),
        "prompt_integrity_status": resolved.get("integrity_status"),
        "prompt_fallback_used": bool(resolved.get("fallback_used", False)),
        "catalog_source": resolved.get("catalog_source"),
    }
    if resolved.get("failure_reason"):
        metadata["prompt_failure_reason"] = resolved["failure_reason"]
    return text, metadata


def _resolution(
    *,
    intent_id: str | None,
    category: str | None,
    route_target: str | None,
    validation_status: str,
    spoken_text: str,
    params: dict[str, Any] | None = None,
    used_session_context: bool = False,
    error_code: str | None = None,
    controller_result: Any = None,
    metadata: dict[str, Any] | None = None,
) -> CommandResolution:
    return CommandResolution(
        intent_id=intent_id,
        category=category,
        route_target=route_target,
        validation_status=validation_status,
        params=dict(params or {}),
        used_session_context=used_session_context,
        spoken_text=spoken_text,
        error_code=error_code,
        controller_result=controller_result,
        metadata=dict(metadata or {}),
    )


def _clamp_speed(value: float) -> float:
    return max(settings_manager.min_speech_speed, min(value, settings_manager.max_speech_speed))


def _extract_numeric_speed(command_text: str | None) -> float | None:
    if not command_text:
        return None
    number_match = re.search(r"(\d+(?:\.\d+)?)", command_text)
    if number_match:
        return float(number_match.group(1))
    lowered = command_text.lower()
    if any(word in lowered for word in ("fast", "ط³ط±ظٹط¹")):
        return 1.4
    if any(word in lowered for word in ("slow", "ط¨ط·ظٹ")):
        return 0.8
    return None


def _extract_face_id(raw_value: Any) -> str | None:
    if isinstance(raw_value, dict):
        if isinstance(raw_value.get("face_id"), str):
            return raw_value["face_id"]
    if isinstance(raw_value, str):
        match = re.search(r"(Face_\d+)", raw_value)
        if match:
            return match.group(1)
    return None


def _infer_language_from_text(command_text: str | None) -> str | None:
    if not command_text:
        return None
    lowered = command_text.lower()
    if any(word in lowered for word in ("arabic", "ط¹ط±ط¨ظٹ", "ط§ظ„ط¹ط±ط¨ظٹط©")):
        return "ar-EG"
    if any(word in lowered for word in ("english", "inglish", "ط§ظ†ط¬ظ„ط´")):
        return "en-US"
    return None


def _infer_gender_from_text(command_text: str | None) -> str | None:
    if not command_text:
        return None
    lowered = command_text.lower()
    if re.search(r"\bfemale\b", lowered) or any(word in lowered for word in ("ط§ظ†ط«ظ‰", "ط£ظ†ط«ظ‰", "ط¨ظ†طھ")):
        return "female"
    if re.search(r"\bmale\b", lowered) or any(word in lowered for word in ("ط°ظƒط±",)):
        return "male"
    return None


def _dialog_metadata(result: dialog_policy.DialogInterpretationResult) -> dict[str, Any]:
    return {
        "dialog_normalized_utterance": result.normalized_utterance,
        "dialog_matched_outcomes": list(result.matched_outcomes),
        "dialog_outcome": result.final_outcome,
        "dialog_safe_precedence_applied": bool(result.safe_precedence_applied),
    }


def _clarification_surface_id(intent_id: str) -> str:
    if intent_id == "set_language":
        return "resolver.clarification.language.required"
    if intent_id == "set_voice_gender":
        return "resolver.clarification.voice.required"
    return "resolver.clarification.failed"


def _activate_dialog_flow(intent_id: str) -> None:
    _clear_stale_follow_up_if_needed(intent_id)


def _build_rejected_resolution(parsed_intent: ParsedCommandIntent | None) -> CommandResolution:
    spoken = _localized(
        "ظ…ط¹ط°ط±ط©طŒ ظ„ظ… ط£ظپظ‡ظ… ظ‡ط°ط§ ط§ظ„ط£ظ…ط±",
        "Sorry, I didn't understand that command.",
    )
    intent_id = parsed_intent.intent_id if parsed_intent else None
    category = parsed_intent.category if parsed_intent else None
    error_code = parsed_intent.rejection_reason if parsed_intent else "unrecognized_command"
    metadata: dict[str, Any] = {}
    if parsed_intent:
        metadata = {
            "score": parsed_intent.score,
            "threshold": parsed_intent.threshold,
            "risk_level": parsed_intent.risk_level,
            "runner_up_intent": parsed_intent.runner_up_intent,
            "runner_up_score": parsed_intent.runner_up_score,
        }
    return _resolution(
        intent_id=intent_id,
        category=category,
        route_target=None,
        validation_status="rejected",
        spoken_text=spoken,
        error_code=error_code,
        metadata=metadata,
    )


def _clear_stale_follow_up_if_needed(intent_id: str) -> None:
    if SESSION_CONTEXT.remaining_follow_ups == 0:
        return
    if intent_id != SESSION_CONTEXT.follow_up_target_intent:
        SESSION_CONTEXT.clear_follow_up()


def _handle_pending_confirmation(text: str | None) -> CommandResolution | None:
    pending_intent = SESSION_CONTEXT.pending_confirmation_intent
    pending_payload = dict(SESSION_CONTEXT.pending_confirmation_payload or {})
    if not pending_intent:
        return None

    dialog_result = dialog_policy.interpret_yes_no_cancel(text)
    dialog_metadata = _dialog_metadata(dialog_result)

    if dialog_result.final_outcome == dialog_policy.OUTCOME_AFFIRMATIVE:
        SESSION_CONTEXT.clear_confirmation()
        return _execute_intent(
            intent_id=pending_intent,
            command_text=text,
            params=pending_payload,
            parsed_intent=None,
            metadata={
                "dialog_flow": "confirmation",
                "confirmation_response": "accepted",
                **dialog_metadata,
            },
        )

    if dialog_result.final_outcome in {dialog_policy.OUTCOME_NEGATIVE, dialog_policy.OUTCOME_CANCEL}:
        SESSION_CONTEXT.clear_confirmation()
        spoken_text, prompt_metadata = _critical_surface_localized("resolver.confirmation.declined")
        return _resolution(
            intent_id=pending_intent,
            category="system",
            route_target="controller",
            validation_status="rejected",
            spoken_text=spoken_text,
            error_code="confirmation_declined",
            metadata={
                "dialog_flow": "confirmation",
                "confirmation_response": "declined",
                **dialog_metadata,
                **prompt_metadata,
            },
        )

    SESSION_CONTEXT.pending_confirmation_attempts += 1
    if SESSION_CONTEXT.pending_confirmation_attempts <= MAX_CONFIRMATION_RETRY_ATTEMPTS:
        spoken_text = _localized(
            "ط¸â€¦ط¸â€  ط¸ظ¾ط·آ¶ط¸â€‍ط¸ئ’ ط¸ئ’ط¸â€  ط¸ث†ط·آ§ط·آ¶ط·آ­ط·آ§ط¸â€¹: ط¸â€ڑط¸â€‍ ط¸â€ ط·آ¹ط¸â€¦ ط¸â€‍ط¸â€‍ط·ع¾ط¸â€ ط¸ظ¾ط¸ظ¹ط·آ° ط·آ£ط¸ث† ط¸â€‍ط·آ§ط¸â€¹ ط¸â€‍ط¸â€‍ط·آ¥ط¸â€‍ط·ط›ط·آ§ط·طŒ.",
            "Please answer clearly: say yes to proceed or no/cancel to stop.",
        )
        settings_manager.speak(spoken_text)
        return _resolution(
            intent_id=pending_intent,
            category="system",
            route_target="controller",
            validation_status="confirmation_required",
            spoken_text=spoken_text,
            error_code="confirmation_retry_required",
            metadata={
                "dialog_flow": "confirmation",
                "confirmation_response": "retry_required",
                **dialog_metadata,
                "confirmation_attempts": SESSION_CONTEXT.pending_confirmation_attempts,
            },
        )

    SESSION_CONTEXT.clear_confirmation()
    spoken_text, prompt_metadata = _critical_surface_localized("resolver.confirmation.expired")
    return _resolution(
        intent_id=pending_intent,
        category="system",
        route_target="controller",
        validation_status="rejected",
        spoken_text=spoken_text,
        error_code="confirmation_expired",
        metadata={
            "dialog_flow": "confirmation",
            "confirmation_response": "expired",
            **dialog_metadata,
            **prompt_metadata,
        },
    )


def _resolve_required_params(intent_id: str, command_text: str | None, params: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    resolved = dict(params)

    if intent_id == "set_language":
        language = resolved.get("language") or _infer_language_from_text(command_text)
        if language:
            resolved["language"] = language
            return resolved, True
        return resolved, False

    if intent_id == "set_voice_gender":
        gender = resolved.get("gender") or _infer_gender_from_text(command_text)
        if gender:
            resolved["gender"] = gender
            return resolved, True
        return resolved, False

    return resolved, True


def _execute_intent(
    *,
    intent_id: str,
    command_text: str | None,
    params: dict[str, Any] | None,
    parsed_intent: ParsedCommandIntent | None,
    metadata: dict[str, Any] | None = None,
) -> CommandResolution:
    catalog_entry = command_parser.COMMAND_CATALOG.get(intent_id)
    category = catalog_entry.category if catalog_entry else None
    route_target = catalog_entry.route_target if catalog_entry else "controller"
    merged_metadata: dict[str, Any] = dict(metadata or {})
    merged_metadata.setdefault("risk_level", catalog_entry.risk_level if catalog_entry else None)

    resolved_params = dict(params or {})
    used_session_context = False

    if intent_id in PARAMETER_REQUIRED_INTENTS:
        resolved_params, has_required_params = _resolve_required_params(intent_id, command_text, resolved_params)
        if not has_required_params:
            if SESSION_CONTEXT.pending_clarification_intent != intent_id:
                _activate_dialog_flow(intent_id)
                SESSION_CONTEXT.pending_clarification_intent = intent_id
                SESSION_CONTEXT.clarification_attempts = 0

            SESSION_CONTEXT.clarification_attempts += 1
            attempt_count = SESSION_CONTEXT.clarification_attempts
            remaining_attempts = max(0, MAX_CLARIFICATION_ATTEMPTS - attempt_count)
            merged_metadata.update(
                {
                    "dialog_flow": "clarification",
                    "clarification_attempt_count": attempt_count,
                    "clarification_remaining_attempts": remaining_attempts,
                }
            )

            if attempt_count >= MAX_CLARIFICATION_ATTEMPTS:
                SESSION_CONTEXT.clear_clarification()
                spoken_text, prompt_metadata = _critical_surface_localized("resolver.clarification.failed")
                return _resolution(
                    intent_id=intent_id,
                    category=category,
                    route_target=route_target,
                    validation_status="failed",
                    spoken_text=spoken_text,
                    error_code="clarification_failed",
                    metadata={**merged_metadata, **prompt_metadata},
                )

            spoken_text, prompt_metadata = _critical_surface_localized(_clarification_surface_id(intent_id))
            return _resolution(
                intent_id=intent_id,
                category=category,
                route_target=route_target,
                validation_status="clarification_required",
                spoken_text=spoken_text,
                error_code="missing_required_parameter",
                metadata={**merged_metadata, **prompt_metadata},
            )
        if SESSION_CONTEXT.pending_clarification_intent == intent_id:
            merged_metadata["dialog_flow"] = "clarification"
            merged_metadata["clarification_resolved"] = True
            SESSION_CONTEXT.clear_clarification()

    _clear_stale_follow_up_if_needed(intent_id)

    if intent_id == "recognize_emotion" and "face_id" not in resolved_params:
        if (
            SESSION_CONTEXT.remaining_follow_ups == 1
            and SESSION_CONTEXT.follow_up_target_intent == "recognize_emotion"
            and SESSION_CONTEXT.last_face_id
        ):
            resolved_params["face_id"] = SESSION_CONTEXT.last_face_id
            used_session_context = True

    try:
        if intent_id in LANGUAGE_COMMANDS:
            language = LANGUAGE_COMMANDS[intent_id]
            controller_result = mc.set_language(language)
            return _resolution(
                intent_id=intent_id,
                category=category,
                route_target=route_target,
                validation_status="ready",
                params={"language": language},
                spoken_text=str(controller_result),
                controller_result=controller_result,
                metadata=merged_metadata,
            )

        if intent_id == "set_language":
            language = resolved_params["language"]
            controller_result = mc.set_language(language)
            return _resolution(
                intent_id=intent_id,
                category=category,
                route_target=route_target,
                validation_status="ready",
                params={"language": language},
                spoken_text=str(controller_result),
                controller_result=controller_result,
                metadata=merged_metadata,
            )

        if intent_id in VOICE_GENDER_COMMANDS:
            gender = VOICE_GENDER_COMMANDS[intent_id]
            controller_result = mc.set_voice_gender(gender=gender)
            return _resolution(
                intent_id=intent_id,
                category=category,
                route_target=route_target,
                validation_status="ready",
                params={"gender": gender},
                spoken_text=str(controller_result),
                controller_result=controller_result,
                metadata=merged_metadata,
            )

        if intent_id == "set_voice_gender":
            gender = resolved_params["gender"]
            controller_result = mc.set_voice_gender(gender=gender)
            return _resolution(
                intent_id=intent_id,
                category=category,
                route_target=route_target,
                validation_status="ready",
                params={"gender": gender},
                spoken_text=str(controller_result),
                controller_result=controller_result,
                metadata=merged_metadata,
            )

        if intent_id in SPEECH_SPEED_PRESETS:
            target_speed = _clamp_speed(SPEECH_SPEED_PRESETS[intent_id])
            controller_result = mc.set_speech_speed(speed=target_speed)
            return _resolution(
                intent_id=intent_id,
                category=category,
                route_target=route_target,
                validation_status="ready",
                params={"speed": target_speed},
                spoken_text=str(controller_result),
                controller_result=controller_result,
                metadata=merged_metadata,
            )

        if intent_id in SPEECH_SPEED_DELTAS:
            target_speed = _clamp_speed(settings_manager.speech_speed + SPEECH_SPEED_DELTAS[intent_id])
            controller_result = mc.set_speech_speed(speed=target_speed)
            return _resolution(
                intent_id=intent_id,
                category=category,
                route_target=route_target,
                validation_status="ready",
                params={"speed": target_speed},
                spoken_text=str(controller_result),
                controller_result=controller_result,
                metadata=merged_metadata,
            )

        if intent_id == "set_speech_speed":
            speed = _extract_numeric_speed(command_text)
            if speed is None:
                speed = settings_manager.default_speech_speed
            target_speed = _clamp_speed(speed)
            controller_result = mc.set_speech_speed(speed=target_speed)
            return _resolution(
                intent_id=intent_id,
                category=category,
                route_target=route_target,
                validation_status="ready",
                params={"speed": target_speed},
                spoken_text=str(controller_result),
                controller_result=controller_result,
                metadata=merged_metadata,
            )

        func = COMMAND_FUNCTION_MAPPING.get(intent_id)
        if not func:
            return _resolution(
                intent_id=intent_id,
                category=category,
                route_target=route_target,
                validation_status="failed",
                spoken_text=_localized(
                    "ظ‡ط°ط§ ط§ظ„ط£ظ…ط± ط؛ظٹط± ظ…ط¯ط¹ظˆظ… ط­ط§ظ„ظٹط§ظ‹.",
                    "This command is not supported yet.",
                ),
                error_code="unsupported_command",
                metadata=merged_metadata,
            )

        controller_result = func(**resolved_params) if resolved_params else func()
        if isinstance(controller_result, dict) and isinstance(controller_result.get("spoken_text"), str):
            spoken_text = controller_result["spoken_text"]
        else:
            spoken_text = str(controller_result)

        controller_status = None
        controller_error_code = None
        if isinstance(controller_result, dict):
            controller_status = controller_result.get("status")
            controller_error_code = controller_result.get("error_code")
            capability_id = controller_result.get("capability_id")
            if capability_id:
                merged_metadata["capability_id"] = capability_id
            if "used_fallback" in controller_result:
                merged_metadata["used_fallback"] = bool(controller_result["used_fallback"])

        if intent_id == "recognize_face" and controller_status in {None, "success"}:
            face_id = resolved_params.get("face_id") or _extract_face_id(controller_result)
            if face_id:
                SESSION_CONTEXT.last_face_id = face_id
            SESSION_CONTEXT.follow_up_source_intent = "recognize_face"
            SESSION_CONTEXT.follow_up_target_intent = "recognize_emotion"
            SESSION_CONTEXT.remaining_follow_ups = 1
            if face_id:
                resolved_params["face_id"] = face_id

        if intent_id == "recognize_emotion":
            if used_session_context:
                SESSION_CONTEXT.clear_follow_up()
            else:
                SESSION_CONTEXT.remaining_follow_ups = 0

        if controller_status in {"timeout", "failed", "unavailable"}:
            return _resolution(
                intent_id=intent_id,
                category=category,
                route_target=route_target,
                validation_status="failed",
                params=resolved_params,
                used_session_context=used_session_context,
                spoken_text=spoken_text,
                controller_result=controller_result,
                error_code=controller_error_code or "capability_failure",
                metadata=merged_metadata,
            )

        if controller_status == "rejected":
            return _resolution(
                intent_id=intent_id,
                category=category,
                route_target=route_target,
                validation_status="rejected",
                params=resolved_params,
                used_session_context=used_session_context,
                spoken_text=spoken_text,
                controller_result=controller_result,
                error_code=controller_error_code or "capability_rejected",
                metadata=merged_metadata,
            )

        return _resolution(
            intent_id=intent_id,
            category=category,
            route_target=route_target,
            validation_status="ready",
            params=resolved_params,
            used_session_context=used_session_context,
            spoken_text=spoken_text,
            controller_result=controller_result,
            metadata=merged_metadata,
        )
    except Exception as err:  # noqa: BLE001
        logger.exception("[RESOLVER] Execution failed for %s", intent_id)
        return _resolution(
            intent_id=intent_id,
            category=category,
            route_target=route_target,
            validation_status="failed",
            spoken_text=_localized("ط­ط¯ط« ط®ط·ط£ ط£ط«ظ†ط§ط، طھظ†ظپظٹط° ط§ظ„ط£ظ…ط±.", "An error occurred while executing the command."),
            error_code="resolver_execution_error",
            metadata={**merged_metadata, "exception": str(err)},
        )


def resolve_command(
    *,
    parsed_intent: ParsedCommandIntent | None = None,
    command_key: str | None = None,
    command_text: str | None = None,
    params: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    runtime_context: dict[str, Any] | None = None,
) -> CommandResolution:
    logger.info("[RESOLVER] Resolving command text=%s key=%s", command_text, command_key)

    pending_confirmation_resolution = _handle_pending_confirmation(command_text)
    if pending_confirmation_resolution is not None:
        return pending_confirmation_resolution

    if SESSION_CONTEXT.pending_clarification_intent:
        pending_intent = SESSION_CONTEXT.pending_clarification_intent
        dialog_result = dialog_policy.interpret_yes_no_cancel(command_text)
        if dialog_result.final_outcome in {dialog_policy.OUTCOME_NEGATIVE, dialog_policy.OUTCOME_CANCEL}:
            SESSION_CONTEXT.clear_clarification()
            spoken_text, prompt_metadata = _critical_surface_localized("resolver.clarification.failed")
            return _resolution(
                intent_id=pending_intent,
                category="settings",
                route_target="settings_manager",
                validation_status="failed",
                spoken_text=spoken_text,
                error_code="clarification_failed",
                metadata={
                    "dialog_flow": "clarification",
                    "clarification_cancelled": True,
                    **_dialog_metadata(dialog_result),
                    **prompt_metadata,
                },
            )

        return _execute_intent(
            intent_id=pending_intent,
            command_text=command_text,
            params={},
            parsed_intent=None,
            metadata={
                "dialog_flow": "clarification",
                "clarification_follow_up": True,
                **_dialog_metadata(dialog_result),
            },
        )

    if parsed_intent is None and command_key is not None:
        entry = command_parser.COMMAND_CATALOG.get(command_key)
        parsed_intent = ParsedCommandIntent(
            raw_text=command_text or "",
            normalized_text=(command_text or "").strip().lower(),
            intent_id=command_key,
            category=entry.category if entry else None,
            risk_level=entry.risk_level if entry else None,
            matched_keyword=None,
            score=100.0,
            threshold=0.0,
            accepted=True,
            rejection_reason=None,
            metadata={},
        )

    if parsed_intent is None:
        parsed_intent = command_parser.parse_command(command_text or "")

    if not parsed_intent.accepted or not parsed_intent.intent_id:
        return _build_rejected_resolution(parsed_intent)

    intent_id = parsed_intent.intent_id
    entry = command_parser.COMMAND_CATALOG.get(intent_id)
    parsed_metadata = {
        "score": parsed_intent.score,
        "threshold": parsed_intent.threshold,
        "matched_keyword": parsed_intent.matched_keyword,
        "risk_level": parsed_intent.risk_level,
    }
    merged_metadata = {**parsed_metadata, **dict(metadata or {})}

    context = dict(runtime_context or {})
    connectivity_snapshot = settings_manager.get_connectivity_state_snapshot()
    effective_network_available = bool(
        context.get(
            "effective_network_available",
            context.get("network_available", connectivity_snapshot.get("effective_network_available", True)),
        )
    )
    override_mode = str(context.get("override_mode", connectivity_snapshot.get("override_mode", "auto")))
    detected_status = str(context.get("detected_status", connectivity_snapshot.get("detected_status", "online")))
    provider_id = str(context.get("provider_id", settings_manager.speech_provider))
    provider_availability = str(context.get("provider_availability", "ready"))
    descriptor = cap_registry.get_default_registry().descriptor_for_intent(intent_id)
    capability_id = descriptor.capability_id if descriptor else None
    requires_network = bool(context.get("requires_network_override", False))
    if descriptor is not None:
        requires_network = requires_network or bool(descriptor.requires_network)
    requires_network = requires_network or intent_id in NETWORK_REQUIRED_INTENTS
    offline_allowlist = context.get("offline_allowlist", settings_manager.offline_allowlisted_capabilities)
    offline_decision = evaluate_offline_execution_policy(
        flow="command",
        capability_id=capability_id,
        provider_id=provider_id,
        requires_network=requires_network,
        effective_network_available=effective_network_available,
        override_mode=override_mode,
        detected_status=detected_status,
        provider_availability=provider_availability,
        offline_allowlist=offline_allowlist,
    )
    merged_metadata.update(
        {
            "offline_policy_decision": offline_decision.decision,
            "requires_network": requires_network,
            "network_available": effective_network_available,
            "effective_network_available": effective_network_available,
            "override_mode": offline_decision.override_mode,
            "detected_status": offline_decision.detected_status,
            "provider_availability": offline_decision.provider_availability,
            "capability_id": capability_id,
            "provider_id": provider_id,
        }
    )
    if offline_decision.decision in {"safe_refusal", "provider_degraded"}:
        spoken_text, prompt_metadata = _critical_surface_localized("runtime.offline.safe_refusal")
        return _resolution(
            intent_id=intent_id,
            category=entry.category if entry else "capability",
            route_target=entry.route_target if entry else "controller",
            validation_status="rejected",
            spoken_text=spoken_text,
            error_code=offline_decision.error_code,
            metadata={**merged_metadata, **prompt_metadata},
        )

    if intent_id in PROTECTED_INTENTS:
        _activate_dialog_flow(intent_id)
        if SESSION_CONTEXT.pending_clarification_intent:
            SESSION_CONTEXT.clear_clarification()
        SESSION_CONTEXT.pending_confirmation_intent = intent_id
        SESSION_CONTEXT.pending_confirmation_payload = dict(params or {})
        SESSION_CONTEXT.pending_confirmation_attempts = 0
        spoken_text, prompt_metadata = _critical_surface_localized("resolver.confirmation.required")
        return _resolution(
            intent_id=intent_id,
            category=entry.category if entry else "system",
            route_target=entry.route_target if entry else "controller",
            validation_status="confirmation_required",
            spoken_text=spoken_text,
            params=dict(params or {}),
            metadata={**merged_metadata, "dialog_flow": "confirmation", **prompt_metadata},
        )

    if SESSION_CONTEXT.pending_clarification_intent and SESSION_CONTEXT.pending_clarification_intent != intent_id:
        SESSION_CONTEXT.clear_clarification()

    return _execute_intent(
        intent_id=intent_id,
        command_text=command_text,
        params=params,
        parsed_intent=parsed_intent,
        metadata=merged_metadata,
    )
