"""Unit tests for deterministic command phrase-hint governance."""

from __future__ import annotations

from core.speech.phrase_hints import (
    COMMAND_PRIORITY_ORDER,
    DEFAULT_CLOUD_COMMAND_HINT_CAP,
    DEFAULT_CLOUD_WAKE_HINT_CAP,
    DEFAULT_COMMAND_HINT_CAP,
    DEFAULT_STRICT_WAKE_GRAMMAR_CAP,
    build_phrase_hint_set,
)


def test_phrase_hints_are_deterministic_for_all_modes() -> None:
    for mode in ("wake", "command", "confirmation", "onboarding"):
        first = build_phrase_hint_set(mode=mode)
        second = build_phrase_hint_set(mode=mode)
        assert first.phrases == second.phrases
        assert first.variant_types == second.variant_types
        assert first.source_catalogs == second.source_catalogs


def test_command_hints_priority_keeps_protected_commands_inside_cap() -> None:
    command_hints = build_phrase_hint_set(mode="command")
    phrases = command_hints.phrases
    assert len(phrases) <= DEFAULT_COMMAND_HINT_CAP
    assert "stop system" in set(phrases)
    assert "cancel" in set(phrases)
    assert phrases.index("stop system") < 15
    assert command_hints.priority_order == COMMAND_PRIORITY_ORDER


def test_command_hints_include_assistive_families_and_variants() -> None:
    command_hints = build_phrase_hint_set(mode="command")
    phrases = set(command_hints.phrases)
    assert "start obstacle detection" in phrases
    assert "recognize face" in phrases
    assert "read text" in phrases
    assert "help me" in phrases
    assert "start obsticle" in phrases
    assert "obsticle detection" in phrases
    assert "read text bel araby" in phrases
    assert {"english", "arabic", "bilingual", "phonetic", "stt_mistake"}.issubset(
        set(command_hints.variant_types)
    )


def test_command_hints_include_arabic_and_bilingual_entries() -> None:
    hints = build_phrase_hint_set(mode="command")
    phrases = set(hints.phrases)
    assert "\u0648\u0642\u0641" in phrases
    assert "\u0627\u0642\u0631\u0623 \u0627\u0644\u0646\u0635" in phrases
    assert "detect obstacle bel araby" in phrases


def test_confirmation_phrase_hints_use_closed_vocabulary_context() -> None:
    hints = build_phrase_hint_set(mode="confirmation", closed_vocabulary_id="confirmation.yes_no")
    phrases = set(hints.phrases)
    assert "yes" in phrases
    assert "no" in phrases
    assert "cancel" in phrases


def test_phrase_hints_are_deduplicated_and_field_safe() -> None:
    hints = build_phrase_hint_set(mode="wake")
    assert len(hints.phrases) == len(set(item.casefold() for item in hints.phrases))
    assert all(item.strip() for item in hints.phrases)
    assert hints.raw_user_content_present is False


def test_wake_hints_include_canonical_and_curated_variant_families() -> None:
    wake_hints = build_phrase_hint_set(mode="wake")
    phrases = set(wake_hints.phrases)
    assert "hi egb" in phrases
    assert "marhaba" in phrases
    assert "hi agency" in phrases
    assert "hi hgb" in phrases
    assert {"canonical", "english", "arabic", "bilingual", "phonetic", "stt_mistake"} == set(
        wake_hints.variant_types
    )


def test_wake_hint_contract_exposes_phase19_cloud_and_strict_caps() -> None:
    wake_hints = build_phrase_hint_set(mode="wake")
    payload = wake_hints.to_dict()
    assert payload["max_cloud_phrases"] == DEFAULT_CLOUD_WAKE_HINT_CAP
    assert payload["max_strict_grammar_phrases"] == DEFAULT_STRICT_WAKE_GRAMMAR_CAP
    assert len(payload["phrases"]) <= DEFAULT_STRICT_WAKE_GRAMMAR_CAP


def test_command_hint_contract_exposes_cloud_and_strict_caps() -> None:
    hints = build_phrase_hint_set(mode="command")
    payload = hints.to_dict()
    assert payload["max_cloud_phrases"] == DEFAULT_CLOUD_COMMAND_HINT_CAP
    assert payload["max_strict_grammar_phrases"] == DEFAULT_COMMAND_HINT_CAP
