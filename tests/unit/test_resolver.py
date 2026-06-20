"""Resolver behavior tests for structured command execution decisions."""

from controllers import capability_registry as cap_registry
from core import parser, resolver


def setup_function() -> None:
    resolver.reset_session_context()


def test_resolver_returns_ready_for_simple_settings_command() -> None:
    parsed = parser.parse_command("switch to english")
    resolution = resolver.resolve_command(parsed_intent=parsed, command_text="switch to english")
    assert resolution.validation_status == "ready"
    assert resolution.intent_id == "set_language_en"
    assert isinstance(resolution.spoken_text, str)
    assert resolution.error_code is None


def test_resolver_clarifies_with_explicit_options_then_fails_after_bounded_retries() -> None:
    first_parse = parser.parse_command("change language")
    first_resolution = resolver.resolve_command(parsed_intent=first_parse, command_text="change language")
    assert first_resolution.validation_status == "clarification_required"
    assert first_resolution.metadata["surface_id"] == "resolver.clarification.language.required"
    assert first_resolution.metadata["clarification_attempt_count"] == 1

    second_parse = parser.parse_command("change language")
    second_resolution = resolver.resolve_command(parsed_intent=second_parse, command_text="change language")
    assert second_resolution.validation_status == "clarification_required"
    assert second_resolution.metadata["clarification_attempt_count"] == 2

    third_parse = parser.parse_command("change language")
    third_resolution = resolver.resolve_command(parsed_intent=third_parse, command_text="change language")
    assert third_resolution.validation_status == "failed"
    assert third_resolution.error_code == "clarification_failed"
    assert third_resolution.metadata["surface_id"] == "resolver.clarification.failed"


def test_resolver_clarification_can_resolve_from_option_only_response() -> None:
    first_parse = parser.parse_command("set language")
    first_resolution = resolver.resolve_command(parsed_intent=first_parse, command_text="set language")
    assert first_resolution.validation_status == "clarification_required"

    second_resolution = resolver.resolve_command(parsed_intent=None, command_text="english")
    assert second_resolution.validation_status == "ready"
    assert second_resolution.params["language"] == "en-US"
    assert second_resolution.metadata["clarification_resolved"] is True


def test_resolver_uses_follow_up_context_for_emotion_once(vision_adapter_factory) -> None:
    cap_registry.set_vision_adapter(
        vision_adapter_factory(
            face_response={
                "status": "success",
                "spoken_text": "Face Face_321 recognized.",
                "payload": {
                    "face_id": "Face_321",
                    "allow_emotion_follow_up": True,
                },
            }
        )
    )
    face_parse = parser.parse_command("recognize face")
    face_resolution = resolver.resolve_command(parsed_intent=face_parse, command_text="recognize face")
    assert face_resolution.validation_status == "ready"

    emotion_parse = parser.parse_command("recognize emotion")
    emotion_resolution = resolver.resolve_command(parsed_intent=emotion_parse, command_text="recognize emotion")
    assert emotion_resolution.validation_status == "ready"
    assert emotion_resolution.used_session_context is True

    context = resolver.get_session_context()
    assert context.remaining_follow_ups == 0


def test_resolver_does_not_arm_emotion_follow_up_when_face_is_unknown(vision_adapter_factory) -> None:
    cap_registry.set_vision_adapter(
        vision_adapter_factory(
            face_response={
                "status": "success",
                "spoken_text": "I can see a face, but I could not identify it.",
                "payload": {
                    "face_id": None,
                    "allow_emotion_follow_up": False,
                    "identified": False,
                },
            }
        )
    )

    face_parse = parser.parse_command("recognize face")
    face_resolution = resolver.resolve_command(parsed_intent=face_parse, command_text="recognize face")

    assert face_resolution.validation_status == "ready"
    context = resolver.get_session_context()
    assert context.remaining_follow_ups == 0
    assert context.last_face_id is None


def test_resolver_requires_confirmation_for_protected_commands() -> None:
    protected_parse = parser.parse_command("stop system")
    confirmation = resolver.resolve_command(parsed_intent=protected_parse, command_text="stop system")
    assert confirmation.validation_status == "confirmation_required"

    confirmed = resolver.resolve_command(parsed_intent=None, command_text="yes")
    assert confirmed.validation_status == "ready"
    assert confirmed.intent_id == "stop_system"


def test_resolver_accepts_affirmative_phrase_family_for_confirmation() -> None:
    protected_parse = parser.parse_command("reset settings")
    confirmation = resolver.resolve_command(parsed_intent=protected_parse, command_text="reset settings")
    assert confirmation.validation_status == "confirmation_required"

    confirmed = resolver.resolve_command(parsed_intent=None, command_text="yes please")
    assert confirmed.validation_status == "ready"
    assert confirmed.intent_id == "reset_settings"


def test_resolver_prefers_safe_non_executing_outcome_for_mixed_confirmation() -> None:
    protected_parse = parser.parse_command("stop system")
    confirmation = resolver.resolve_command(parsed_intent=protected_parse, command_text="stop system")
    assert confirmation.validation_status == "confirmation_required"

    rejected = resolver.resolve_command(parsed_intent=None, command_text="yes cancel")
    assert rejected.validation_status == "rejected"
    assert rejected.error_code == "confirmation_declined"
    assert rejected.metadata["dialog_safe_precedence_applied"] is True


def test_resolver_confirmation_noise_retries_once_then_expires() -> None:
    protected_parse = parser.parse_command("reset settings")
    confirmation = resolver.resolve_command(parsed_intent=protected_parse, command_text="reset settings")
    assert confirmation.validation_status == "confirmation_required"

    retry = resolver.resolve_command(parsed_intent=None, command_text="not sure")
    assert retry.validation_status == "confirmation_required"
    assert retry.error_code == "confirmation_retry_required"
    assert retry.metadata["confirmation_attempts"] == 1

    expired = resolver.resolve_command(parsed_intent=None, command_text="still unclear")
    assert expired.validation_status == "rejected"
    assert expired.error_code == "confirmation_expired"
    assert expired.metadata["confirmation_response"] == "expired"


def test_resolver_clears_stale_follow_up_when_confirmation_starts(vision_adapter_factory) -> None:
    cap_registry.set_vision_adapter(vision_adapter_factory())
    face_parse = parser.parse_command("recognize face")
    resolver.resolve_command(parsed_intent=face_parse, command_text="recognize face")
    assert resolver.get_session_context().remaining_follow_ups == 1

    stop_parse = parser.parse_command("stop system")
    confirmation = resolver.resolve_command(parsed_intent=stop_parse, command_text="stop system")
    assert confirmation.validation_status == "confirmation_required"
    assert resolver.get_session_context().remaining_follow_ups == 0


def test_resolver_clears_stale_follow_up_when_clarification_starts(vision_adapter_factory) -> None:
    cap_registry.set_vision_adapter(vision_adapter_factory())
    face_parse = parser.parse_command("recognize face")
    resolver.resolve_command(parsed_intent=face_parse, command_text="recognize face")
    assert resolver.get_session_context().remaining_follow_ups == 1

    clarify_parse = parser.parse_command("set voice gender")
    clarification = resolver.resolve_command(parsed_intent=clarify_parse, command_text="set voice gender")
    assert clarification.validation_status == "clarification_required"
    assert resolver.get_session_context().remaining_follow_ups == 0


def test_resolver_keeps_recognition_metadata_for_downstream_observability() -> None:
    parsed = parser.parse_command(
        "switch to english",
        recognition_metadata={
            "recognition_path": "local_first",
            "confidence_available": False,
        },
    )
    resolution = resolver.resolve_command(
        parsed_intent=parsed,
        command_text="switch to english",
        metadata=parsed.metadata,
    )
    assert resolution.validation_status == "ready"
    assert resolution.metadata["recognition"]["recognition_path"] == "local_first"
