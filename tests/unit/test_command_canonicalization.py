"""Unit coverage for Phase 14 transcript canonicalization behavior."""

from __future__ import annotations

from core.command_post_processing import process_command_transcript


def test_canonicalization_repairs_alias_and_confusion_pairs() -> None:
    outcome = process_command_transcript("mail")
    assert outcome.post_processing_status == "normalized"
    assert outcome.canonical_command_text == "male"
    assert outcome.confusion_pair_id == "voice.male_mail"


def test_canonicalization_closed_choice_accepts_in_set_answer() -> None:
    outcome = process_command_transcript(
        "yes please",
        dictionary_mode="closed_choice",
        closed_vocabulary_id="confirmation.yes_no",
        closed_vocabulary=("yes", "no", "cancel"),
    )
    assert outcome.post_processing_status in {"normalized", "unchanged"}
    assert outcome.canonical_command_text == "yes"
    assert outcome.dictionary_mode == "closed_choice"


def test_canonicalization_closed_choice_out_of_set_returns_constrained_retry() -> None:
    outcome = process_command_transcript(
        "maybe later",
        dictionary_mode="closed_choice",
        closed_vocabulary_id="confirmation.yes_no",
        closed_vocabulary=("yes", "no"),
    )
    assert outcome.post_processing_status == "constrained_retry"
    assert "out_of_closed_vocabulary" in outcome.ambiguity_flags
    assert outcome.canonical_command_text == ""

