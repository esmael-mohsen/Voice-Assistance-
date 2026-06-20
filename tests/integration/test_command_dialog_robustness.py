"""Integration coverage for confirmation, clarification, and follow-up isolation."""

from __future__ import annotations

import pytest

from controllers import capability_registry as cap_registry
from core import resolver
from core.dispatcher import dispatch


@pytest.fixture(autouse=True)
def _reset_dialog_with_fake_vision(vision_adapter_factory):
    resolver.reset_session_context()
    cap_registry.set_vision_adapter(vision_adapter_factory())
    yield
    resolver.reset_session_context()


def test_confirmation_retries_once_then_expires_safely() -> None:
    first = dispatch("stop system")
    assert first.status == "confirmation_required"

    second = dispatch("maybe later")
    assert second.status == "confirmation_required"
    assert second.error_code == "confirmation_retry_required"

    third = dispatch("still not sure")
    assert third.status == "rejected"
    assert third.error_code == "confirmation_expired"


def test_pending_clarification_takes_priority_over_unrelated_new_command() -> None:
    first = dispatch("set language")
    assert first.status == "clarification_required"
    assert first.intent_id == "set_language"

    second = dispatch("start obstacle detection")
    assert second.status == "clarification_required"
    assert second.intent_id == "set_language"


def test_pending_clarification_can_be_cancelled_safely() -> None:
    first = dispatch("set voice gender")
    assert first.status == "clarification_required"

    second = dispatch("cancel")
    assert second.status == "failed"
    assert second.error_code == "clarification_failed"
    assert second.metadata.get("clarification_cancelled") is True


def test_follow_up_state_does_not_leak_into_confirmation_flow() -> None:
    face = dispatch("recognize face")
    assert face.status == "success"
    assert resolver.get_session_context().remaining_follow_ups == 1

    confirm = dispatch("stop system")
    assert confirm.status == "confirmation_required"
    assert resolver.get_session_context().remaining_follow_ups == 0

    approved = dispatch("yes please")
    assert approved.status == "success"
    assert approved.intent_id == "stop_system"


def test_background_noise_confirmation_retries_then_expires_safely() -> None:
    first = dispatch("reset settings")
    assert first.status == "confirmation_required"

    second = dispatch("hmm maybe")
    assert second.status == "confirmation_required"
    assert second.error_code == "confirmation_retry_required"

    third = dispatch("static noise only")
    assert third.status == "rejected"
    assert third.error_code == "confirmation_expired"


def test_mid_dialog_language_change_resolves_pending_clarification() -> None:
    first = dispatch("set language")
    assert first.status == "clarification_required"

    second = dispatch("arabic")
    assert second.status == "success"
    assert second.payload is not None
    assert second.payload["params"]["language"] == "ar-EG"


def test_stale_follow_up_context_does_not_reenter_after_clarification() -> None:
    face = dispatch("recognize face")
    assert face.status == "success"
    assert resolver.get_session_context().remaining_follow_ups == 1

    clarification = dispatch("set voice gender")
    assert clarification.status == "clarification_required"
    assert resolver.get_session_context().remaining_follow_ups == 0

    dispatch("cancel")
    follow_up_reentry = dispatch("recognize emotion")
    assert follow_up_reentry.status in {"success", "failed", "rejected"}
    assert follow_up_reentry.metadata.get("used_session_context") is False


def test_mixed_language_uncertain_phrase_stays_non_executing() -> None:
    mixed_uncertain = dispatch("stop system maybe بالعربي")
    assert mixed_uncertain.status in {"confirmation_required", "rejected"}
