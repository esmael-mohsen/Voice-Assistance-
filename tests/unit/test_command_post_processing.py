"""Unit coverage for command post-processing and canonicalization."""

from core.command_post_processing import canonicalize_command_text, process_command_transcript


def test_post_processing_repairs_common_english_substitutions() -> None:
    outcome = process_command_transcript("reed txt")
    assert outcome.post_processing_status == "normalized"
    assert outcome.normalized_transcript == "read text"
    assert outcome.canonical_command_text == "read text"
    assert "en.read_text.reed_to_read" in outcome.substitution_ids
    assert "en.read_text.txt_to_text" in outcome.substitution_ids


def test_post_processing_marks_mixed_language_hints() -> None:
    outcome = process_command_transcript("start obstacle بالعربي")
    assert "ar" in outcome.language_hints
    assert "en" in outcome.language_hints
    assert "mixed" in outcome.language_hints


def test_post_processing_flags_conflicting_alternatives() -> None:
    outcome = process_command_transcript(
        "start system",
        alternative_transcripts=["start system", "stop system"],
    )
    assert "conflicting_alternatives" in outcome.ambiguity_flags


def test_post_processing_rejects_empty_transcript() -> None:
    outcome = process_command_transcript("   ")
    assert outcome.post_processing_status == "rejected"
    assert "empty_transcript" in outcome.ambiguity_flags


def test_canonicalize_command_text_returns_parser_ready_phrase() -> None:
    canonical = canonicalize_command_text("o c r")
    assert canonical == "ocr"


def test_wake_prefix_is_removed_from_command_transcript() -> None:
    outcome = process_command_transcript("hi egb stop system")
    assert outcome.canonical_command_text == "stop system"
    assert "wake.prefix_removed" in outcome.substitution_ids


def test_wake_only_phrase_does_not_become_actionable_command() -> None:
    outcome = process_command_transcript("hi egb")
    assert outcome.post_processing_status == "rejected"
    assert "empty_after_normalization" in outcome.ambiguity_flags


def test_language_switch_arab_short_form_canonicalizes_to_arabic() -> None:
    outcome = process_command_transcript("switch language to Arab")
    assert outcome.canonical_command_text == "switch to arabic"
    assert "en.language.switch_word_order_arab_to_arabic" in outcome.substitution_ids


def test_ocr_stt_variants_canonicalize_to_start_ocr() -> None:
    cases = {
        "OCR please": "en.ocr.please_to_start",
        "\u0627\u0648 \u0633\u064a \u0627\u0631 \u0628\u0644\u064a": "ar.ocr.letters_please_to_start",
        "put on a ticket to the diction": "en.ocr.ticket_diction_to_text_detection",
        "take us to detection": "en.ocr.take_us_to_text_detection",
    }

    for transcript, rule_id in cases.items():
        outcome = process_command_transcript(transcript)
        assert outcome.canonical_command_text == "start ocr"
        assert rule_id in outcome.substitution_ids


def test_arabic_enable_ocr_letters_canonicalize_to_enable_ocr() -> None:
    outcome = process_command_transcript("\u0627\u0646\u064a\u0628\u0644 \u0627\u0648 \u0633\u064a \u0627\u0631")

    assert outcome.canonical_command_text == "enable ocr"
    assert "ar.ocr.enable_letters" in outcome.substitution_ids


def test_natural_short_capability_commands_canonicalize_to_actions() -> None:
    cases = {
        "put on the obstacle detection please": "start obstacle detection",
        "put en obstacle detection please": "start obstacle detection",
        "run obstacle detection": "start obstacle detection",
        "banana obstacle detection": "start obstacle detection",
        "rannoch obstacle detection please": "start obstacle detection",
        "disable OBD": "disable obstacle detection",
        "obstacle detection": "start obstacle detection",
        "obstacle collection please": "start obstacle detection",
        "money": "start money detection",
        "money detection": "start money detection",
        "run the money detection": "start money detection",
        "run the money debt": "start money detection",
        "run a money detection": "start money detection",
        "\u0631\u0646\u0627 \u0645\u0627\u0646\u064a \u062f\u064a\u062a\u0643\u0634\u0646": "start money detection",
        "run the fish recognition": "face recognition",
        "\u0631\u0646\u0627 \u0641\u064a\u0633 \u0643\u0648\u0631\u0646\u064a\u0634": "face recognition",
        "emot": "recognize emotion",
        "emotion please": "recognize emotion",
        "\u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649": "start ocr",
        "\u0634\u063a\u0644 \u0627\u0644\u062a\u0639\u0631\u0641": "start ocr",
        "\u0634\u063a\u0644 \u0644\u064a \u0627\u0644\u062a\u0639\u0631\u0641": "start ocr",
        "\u0634\u063a\u0644 \u0644\u064a \u0627\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649": "start ocr",
        "\u0634\u063a\u0644 \u0644\u064a \u0627\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0646\u0635\u0648\u0635": "start ocr",
        "\u0634\u063a\u0644 \u0627\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0646\u0635\u0648\u0635": "start ocr",
        "\u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0646\u0635\u0648\u0635": "start ocr",
        "\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0646\u0635\u0648\u0635": "start ocr",
        "\u0627\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0646\u0635\u0648\u0635": "start ocr",
        "\u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0648\u062c\u0647": "face recognition",
        "\u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0648\u062c\u0648\u0647": "face recognition",
        "\u0627\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0648\u0634": "face recognition",
        "\u0634\u063a\u0644 \u0627\u0644\u0645\u0634\u0627\u0639\u0631": "recognize emotion",
        "\u0634\u063a\u0644 \u0643\u0634\u0641 \u0627\u0644\u0641\u0644\u0648\u0633": "start money detection",
        "\u0648\u0642\u0641 \u0627\u0644\u0645\u0627\u0646\u064a": "disable money detection",
        "\u0634\u063a\u0644 \u0627\u0644\u0639\u0648\u0627\u0626\u0642": "start obstacle detection",
        "\u0648\u0642\u0641 \u0627\u0644\u0639\u0648\u0627\u0626\u0642": "disable obstacle detection",
    }

    for transcript, canonical in cases.items():
        outcome = process_command_transcript(transcript)
        assert outcome.canonical_command_text == canonical
        assert outcome.post_processing_status == "normalized"
