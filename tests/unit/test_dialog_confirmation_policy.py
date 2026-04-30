"""Unit coverage for shared confirmation and clarification dialog policy."""

from __future__ import annotations

from core import dialog_policy


def test_dialog_policy_accepts_common_affirmative_variants() -> None:
    cases = ("yes", "yes please", "okay", "confirm", "\u0627\u064a\u0648\u0647", "\u062a\u0645\u0627\u0645")
    for utterance in cases:
        result = dialog_policy.interpret_yes_no_cancel(utterance)
        assert result.final_outcome == dialog_policy.OUTCOME_AFFIRMATIVE
        assert dialog_policy.OUTCOME_AFFIRMATIVE in result.matched_outcomes


def test_dialog_policy_accepts_negative_and_cancel_variants() -> None:
    negative_cases = ("no", "nope", "do not", "\u0644\u0627")
    cancel_cases = ("cancel", "stop", "\u0627\u0644\u063a\u0627\u0621")

    for utterance in negative_cases:
        result = dialog_policy.interpret_yes_no_cancel(utterance)
        assert result.final_outcome == dialog_policy.OUTCOME_NEGATIVE

    for utterance in cancel_cases:
        result = dialog_policy.interpret_yes_no_cancel(utterance)
        assert result.final_outcome == dialog_policy.OUTCOME_CANCEL


def test_dialog_policy_mixed_yes_and_cancel_prefers_safe_outcome() -> None:
    result = dialog_policy.interpret_yes_no_cancel("yes please cancel it")
    assert result.final_outcome == dialog_policy.OUTCOME_CANCEL
    assert result.safe_precedence_applied is True


def test_dialog_policy_mixed_yes_and_negative_prefers_safe_outcome() -> None:
    result = dialog_policy.interpret_yes_no_cancel("yes but no")
    assert result.final_outcome == dialog_policy.OUTCOME_NEGATIVE
    assert result.safe_precedence_applied is True


def test_dialog_policy_mixed_arabic_affirmative_and_cancel_prefers_cancel() -> None:
    result = dialog_policy.interpret_yes_no_cancel("ايوه الغاء")
    assert result.final_outcome == dialog_policy.OUTCOME_CANCEL
    assert result.safe_precedence_applied is True


def test_dialog_policy_unmatched_text_stays_non_executing() -> None:
    result = dialog_policy.interpret_yes_no_cancel("maybe later")
    assert result.final_outcome == dialog_policy.OUTCOME_UNMATCHED
    assert result.matched_outcomes == ()


def test_is_affirmative_only_returns_true_for_affirmative_outcome() -> None:
    assert dialog_policy.is_affirmative("yes please") is True
    assert dialog_policy.is_affirmative("no") is False
    assert dialog_policy.is_affirmative("cancel") is False
    assert dialog_policy.is_affirmative("not sure") is False
