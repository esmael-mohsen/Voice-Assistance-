"""Unit coverage for Phase 16 turn-taking window policy."""

from core.turn_taking import (
    build_turn_window,
    is_global_safety_command,
    listening_status_for_window,
    should_accept_preemption,
)


def test_turn_taking_window_allows_barge_in_for_onboarding_prompt() -> None:
    window = build_turn_window(prompt_surface_id="runtime.onboarding.language")
    assert window.status == "speaking_with_barge_in"
    assert window.barge_in_allowed is True
    assert window.closed_vocabulary_id == "onboarding.language_choice"
    assert window.global_safety_only_preemption is False


def test_turn_taking_window_blocks_barge_in_for_protected_confirmation() -> None:
    window = build_turn_window(prompt_surface_id="resolver.confirmation.required")
    assert window.status == "speaking_only"
    assert window.barge_in_allowed is False
    assert window.global_safety_only_preemption is True
    assert listening_status_for_window(window) == "closed_vocabulary_listening"


def test_turn_taking_preemption_accepts_only_global_safety_for_protected_windows() -> None:
    window = build_turn_window(prompt_surface_id="resolver.confirmation.required")
    assert should_accept_preemption(utterance="stop now", window=window) is True
    assert should_accept_preemption(utterance="tell me weather", window=window) is False


def test_global_safety_detector_supports_arabic_and_english_aliases() -> None:
    assert is_global_safety_command("cancel this") is True
    assert is_global_safety_command("إلغاء") is True
    assert is_global_safety_command("continue please") is False

