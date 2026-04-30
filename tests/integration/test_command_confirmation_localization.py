"""Integration coverage for confirmation and clarification localization metadata."""

from __future__ import annotations

from core import parser, resolver


def setup_function() -> None:
    resolver.reset_session_context()


def test_protected_command_confirmation_uses_approved_prompt_key(
    isolated_settings_manager,
) -> None:
    isolated_settings_manager.apply_settings_snapshot({"language": "ar-EG"}, persist=False)
    parsed = parser.parse_command("stop system")

    confirmation = resolver.resolve_command(parsed_intent=parsed, command_text="stop system")

    assert confirmation.validation_status == "confirmation_required"
    assert confirmation.metadata["surface_id"] == "resolver.confirmation.required"
    assert confirmation.metadata["prompt_key"] == "confirmation_required"
    assert confirmation.metadata["prompt_integrity_status"] in {"valid", "repaired", "fallback_used"}


def test_confirmation_decline_uses_catalog_backed_prompt_metadata(
    isolated_settings_manager,
) -> None:
    isolated_settings_manager.apply_settings_snapshot({"language": "ar-EG"}, persist=False)
    parsed = parser.parse_command("reset settings")
    resolver.resolve_command(parsed_intent=parsed, command_text="reset settings")

    declined = resolver.resolve_command(parsed_intent=None, command_text="لا")

    assert declined.validation_status == "rejected"
    assert declined.error_code == "confirmation_declined"
    assert declined.metadata["surface_id"] == "resolver.confirmation.declined"
    assert declined.metadata["prompt_key"] == "confirmation_declined"


def test_confirmation_prompt_repair_metadata_when_catalog_entry_missing(
    isolated_settings_manager,
) -> None:
    isolated_settings_manager.apply_settings_snapshot({"language": "ar-EG"}, persist=False)
    isolated_settings_manager._critical_prompt_catalog["confirmation_required"]["ar"] = ""
    isolated_settings_manager._repaired_prompt_keys = set()

    parsed = parser.parse_command("stop system")
    confirmation = resolver.resolve_command(parsed_intent=parsed, command_text="stop system")

    assert confirmation.validation_status == "confirmation_required"
    assert confirmation.metadata["surface_id"] == "resolver.confirmation.required"
    assert confirmation.metadata["prompt_integrity_status"] in {"repaired", "fallback_used"}


def test_mixed_confirmation_cues_keep_safe_non_executing_outcome(
    isolated_settings_manager,
) -> None:
    isolated_settings_manager.apply_settings_snapshot({"language": "en-US"}, persist=False)
    parsed = parser.parse_command("stop system")
    resolver.resolve_command(parsed_intent=parsed, command_text="stop system")

    mixed = resolver.resolve_command(parsed_intent=None, command_text="yes cancel")

    assert mixed.validation_status == "rejected"
    assert mixed.error_code == "confirmation_declined"
    assert mixed.metadata["dialog_outcome"] == "cancel"
    assert mixed.metadata["dialog_safe_precedence_applied"] is True


def test_clarification_prompt_uses_language_specific_surface_metadata(
    isolated_settings_manager,
) -> None:
    isolated_settings_manager.apply_settings_snapshot({"language": "en-US"}, persist=False)
    parsed = parser.parse_command("set language")

    clarification = resolver.resolve_command(parsed_intent=parsed, command_text="set language")

    assert clarification.validation_status == "clarification_required"
    assert clarification.metadata["surface_id"] == "resolver.clarification.language.required"
    assert clarification.metadata["prompt_key"] == "clarification_language_required"
    assert clarification.metadata["prompt_integrity_status"] in {"valid", "repaired", "fallback_used"}


def test_protected_confirmation_still_required_when_recognition_metadata_is_uncertain(
    isolated_settings_manager,
) -> None:
    isolated_settings_manager.apply_settings_snapshot({"language": "en-US"}, persist=False)
    parsed = parser.parse_command(
        "stop system",
        recognition_metadata={
            "recognition_path": "fallback",
            "confidence_available": True,
            "confidence_score": 0.4,
        },
    )
    confirmation = resolver.resolve_command(parsed_intent=parsed, command_text="stop system")
    assert confirmation.validation_status == "confirmation_required"
