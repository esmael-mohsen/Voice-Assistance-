"""Smoke validation for Phase 9 confirmation and clarification quickstart paths."""

from __future__ import annotations

from core import resolver
from core.dispatcher import dispatch


def setup_function() -> None:
    resolver.reset_session_context()


def test_bilingual_protected_confirmation_variants_execute_once() -> None:
    for utterance in ("yes please", "ايوه", "تمام"):
        first = dispatch("stop system")
        assert first.status == "confirmation_required"
        second = dispatch(utterance)
        assert second.status == "success"
        assert second.intent_id == "stop_system"


def test_mixed_confirmation_cues_stay_non_executing() -> None:
    first = dispatch("reset settings")
    assert first.status == "confirmation_required"

    second = dispatch("yes cancel")
    assert second.status == "rejected"
    assert second.error_code == "confirmation_declined"
    assert second.metadata.get("dialog_safe_precedence_applied") is True


def test_parameter_clarification_resolves_or_stops_safely() -> None:
    first = dispatch("set language")
    assert first.status == "clarification_required"

    resolved = dispatch("english")
    assert resolved.status == "success"
    assert resolved.payload is not None
    assert resolved.payload["params"]["language"] == "en-US"

    failed_first = dispatch("set voice gender")
    failed_second = dispatch("whatever")
    failed_third = dispatch("still unclear")
    assert failed_first.status == "clarification_required"
    assert failed_second.status == "clarification_required"
    assert failed_third.status == "failed"
    assert failed_third.error_code == "clarification_failed"


def test_follow_up_context_is_cleared_when_clarification_starts() -> None:
    face = dispatch("recognize face")
    assert face.status == "success"
    assert resolver.get_session_context().remaining_follow_ups == 1

    clarification = dispatch("set voice gender")
    assert clarification.status == "clarification_required"
    assert resolver.get_session_context().remaining_follow_ups == 0

    resolved = dispatch("female")
    assert resolved.status == "success"
    assert resolved.intent_id == "set_voice_gender"
    assert resolved.metadata.get("used_session_context") is False


def test_phase13_protected_command_stays_confirmation_required_with_uncertain_metadata() -> None:
    first = dispatch(
        "stop system",
        recognition_metadata={
            "recognition_path": "fallback",
            "confidence_available": True,
            "confidence_score": 0.4,
        },
    )
    assert first.status == "confirmation_required"
