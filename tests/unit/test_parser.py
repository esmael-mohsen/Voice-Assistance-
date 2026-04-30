"""Regression coverage for command parser hardening."""

from core import parser


def test_parser_accepts_curated_bilingual_everyday_cases(bilingual_everyday_cases) -> None:
    for case in bilingual_everyday_cases:
        parsed = parser.parse_command(case.text)
        assert parsed.accepted is True
        assert parsed.intent_id == case.expected_intent
        assert parsed.rejection_reason is None
        assert parsed.category in {"capability", "settings", "system"}
        assert parsed.score >= parsed.threshold


def test_parser_rejects_unrelated_input_with_reason_code() -> None:
    parsed = parser.parse_command("please play a movie now")
    assert parsed.accepted is False
    assert parsed.rejection_reason in {"below_threshold", "ambiguous"}
    assert parsed.score <= parsed.threshold


def test_parser_accepts_natural_sentence_with_embedded_command() -> None:
    parsed = parser.parse_command("could you please start obstacle detection now")
    assert parsed.accepted is True
    assert parsed.intent_id == "enable_obstacle_detection"


def test_parser_accepts_language_switch_in_longer_phrase() -> None:
    parsed = parser.parse_command("please switch to english now")
    assert parsed.accepted is True
    assert parsed.intent_id == "set_language_en"


def test_parser_applies_protected_system_safeguards() -> None:
    parsed = parser.parse_command("stop assistant now")
    # This phrase is close to risky shutdown language and should not auto-trigger.
    if parsed.intent_id == "stop_system":
        assert parsed.accepted is False
    assert parsed.risk_level in {"normal", "elevated", "protected"}


def test_parser_classifies_system_risk_levels() -> None:
    protected = parser.parse_command("stop system")
    elevated = parser.parse_command("start system")
    assert protected.intent_id == "stop_system"
    assert protected.risk_level == "protected"
    assert elevated.intent_id == "start_system"
    assert elevated.risk_level == "elevated"


def test_parser_returns_structured_metadata_for_dispatcher() -> None:
    parsed = parser.parse_command("start obstacle detection")
    assert "normalized_text" in parsed.metadata
    assert parsed.metadata["normalized_text"]
    assert parsed.matched_keyword
    assert parsed.threshold > 0


def test_parser_uses_canonical_command_text_when_provided() -> None:
    parsed = parser.parse_command(
        "reed txt",
        canonical_command_text="read text",
        recognition_metadata={"recognition_path": "local_first"},
    )
    assert parsed.normalized_text == "read text"
    assert parsed.metadata["canonical_command_text"] == "read text"
    assert parsed.metadata["recognition"]["recognition_path"] == "local_first"


def test_parser_rejects_unexpected_unicode_sequences() -> None:
    parsed = parser.parse_command("start obstacle detection\u0007")
    assert parsed.accepted is False
    assert parsed.rejection_reason == "unexpected_unicode"


def test_parser_preserves_recognition_closed_vocabulary_metadata() -> None:
    parsed = parser.parse_command(
        "yes",
        canonical_command_text="yes",
        recognition_metadata={
            "recognition_path": "rescue",
            "closed_vocabulary_id": "confirmation.yes_no",
            "dictionary_bias_applied": True,
        },
    )
    assert parsed.metadata["recognition"]["recognition_path"] == "rescue"
    assert parsed.metadata["recognition"]["closed_vocabulary_id"] == "confirmation.yes_no"
