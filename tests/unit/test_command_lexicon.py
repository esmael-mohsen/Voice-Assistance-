from __future__ import annotations

from core import parser as command_parser
from core.command_post_processing import process_command_transcript
from core.lexicon.loader import load_command_lexicon
from core.speech.phrase_hints import build_phrase_hint_set
from scripts.diagnose_command import diagnose_command


def test_command_lexicon_loads_and_exposes_required_intents() -> None:
    lexicon = load_command_lexicon()

    for intent_id in (
        "enable_OCR",
        "enable_vision",
        "disable_vision",
        "recognize_face",
        "recognize_emotion",
        "enable_money_detection",
        "enable_obstacle_detection",
        "set_language_ar",
        "stop_system",
    ):
        assert intent_id in lexicon.intents
        assert lexicon.intents[intent_id].canonical
        assert lexicon.intents[intent_id].all_phrases()


def test_parser_catalog_is_enriched_from_command_lexicon() -> None:
    transcript = "\u0627\u0641\u062a\u062d \u0642\u0631\u0627\u0621\u0629 \u0627\u0644\u0646\u0635\u0648\u0635"

    parsed = command_parser.parse_command(transcript)

    assert parsed.accepted
    assert parsed.intent_id == "enable_OCR"


def test_post_processing_uses_lexicon_alias_and_pattern_rules() -> None:
    direct = process_command_transcript("there's really tired pharmacist")
    patterned = process_command_transcript("\u0627\u0641\u062a\u062d \u0627\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0648\u062c\u0648\u0647")

    assert direct.canonical_command_text == "start ocr"
    assert "lexicon.enable_OCR.stt_mistakes" in direct.substitution_ids
    assert patterned.canonical_command_text == "face recognition"
    assert "ar.face.start_face_recognition" in patterned.substitution_ids


def test_command_phrase_hints_include_lexicon_phrases() -> None:
    hints = build_phrase_hint_set(mode="command")

    assert "\u0634\u063a\u0644 \u0644\u064a \u0627\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0646\u0635\u0648\u0635" in hints.phrases
    assert "there's really tired pharmacist" in hints.phrases


def test_diagnose_command_reports_execution_decision() -> None:
    report = diagnose_command("\u0634\u063a\u0644 \u0627\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0646\u0635\u0648\u0635")

    assert report["canonical"] == "start ocr"
    assert report["intent_id"] == "enable_OCR"
    assert report["accepted"] is True
    assert report["decision"] == "execute"
