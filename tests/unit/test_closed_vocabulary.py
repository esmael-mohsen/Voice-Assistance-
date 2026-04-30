"""Unit coverage for Phase 16 closed-vocabulary registry behavior."""

from core.closed_vocabulary import (
    closed_vocabulary_choices,
    closed_vocabulary_context,
    is_global_safety_preemption,
    match_closed_vocabulary,
    resolve_closed_vocabulary_id,
)


def test_closed_vocabulary_alias_resolution_maps_legacy_id() -> None:
    assert resolve_closed_vocabulary_id("confirmation.yes_no") == "confirmation.yes_no_cancel"


def test_closed_vocabulary_context_exposes_bilingual_choices() -> None:
    context = closed_vocabulary_context("onboarding.language_choice")
    assert context is not None
    choices = closed_vocabulary_choices("onboarding.language_choice")
    assert "english" in choices
    assert "عربي" in choices


def test_closed_vocabulary_match_supports_exact_aliases() -> None:
    match = match_closed_vocabulary(
        utterance="yes please",
        vocabulary_id="confirmation.yes_no_cancel",
    )
    assert match is not None
    assert match.option_id == "affirmative"
    assert match.canonical_value == "yes"


def test_closed_vocabulary_handles_common_stt_choice_variants() -> None:
    female = match_closed_vocabulary(
        utterance="في ميل",
        vocabulary_id="onboarding.voice_choice",
    )
    normal = match_closed_vocabulary(
        utterance="Norman",
        vocabulary_id="onboarding.speed_choice",
    )
    assert female is not None
    assert female.option_id == "female"
    assert normal is not None
    assert normal.option_id == "normal"


def test_closed_vocabulary_match_rejects_out_of_domain_answer() -> None:
    match = match_closed_vocabulary(
        utterance="play music",
        vocabulary_id="confirmation.yes_no_cancel",
    )
    assert match is None


def test_closed_vocabulary_global_safety_preemption_detector() -> None:
    assert is_global_safety_preemption("stop system now") is True
    assert is_global_safety_preemption("توقف") is True
    assert is_global_safety_preemption("switch language") is False
