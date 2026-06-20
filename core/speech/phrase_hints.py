"""Deterministic phrase hints for cloud STT and strict local fallback."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Sequence

from core.closed_vocabulary import closed_vocabulary_choices
from core.lexicon.loader import load_command_lexicon

_WHITESPACE = re.compile(r"\s+")

PHRASE_HINT_MODES: frozenset[str] = frozenset({"wake", "command", "confirmation", "onboarding"})
DEFAULT_COMMAND_HINT_CAP = 220
DEFAULT_CLOUD_COMMAND_HINT_CAP = 72
DEFAULT_STRICT_WAKE_GRAMMAR_CAP = 32
DEFAULT_CLOUD_WAKE_HINT_CAP = 24

COMMAND_PRIORITY_ORDER: tuple[str, ...] = (
    "protected_safety",
    "parser_catalog",
    "assistive_wearable",
    "arabic",
    "bilingual_phonetic",
    "common_stt_mistakes",
)

COMMAND_SOURCE_CATALOGS: tuple[str, ...] = (
    "safety_critical_commands",
    "core.lexicon.command_lexicon",
    "core.parser.COMMAND_CATALOG",
    "assistive_phrases",
    "arabic_variants",
    "bilingual_variants",
    "phonetic_variants",
    "stt_mistake_variants",
)

_WAKE_ALIASES: tuple[str, ...] = (
    "hi egb",
    "hey egb",
    "hello egb",
    "marhaba",
    "\u0645\u0631\u062d\u0628\u0627",
    "hi agency",
    "hi hgb",
    "hay egy bee",
    "hai e g b",
    "high e g b",
    "\u0647\u0627\u064a \u0627\u064a \u062c\u064a \u0628\u064a",
    "\u0627\u0647\u0644\u0627 \u0627\u064a \u062c\u064a \u0628\u064a",
    "hi egb please",
)
_SAFETY_CRITICAL_COMMANDS: tuple[str, ...] = (
    "stop system",
    "system stop",
    "cancel",
    "emergency stop",
    "reset settings",
    "\u0648\u0642\u0641",  # stop
    "\u0625\u0644\u063a\u0627\u0621",  # cancel
)
_ASSISTIVE_COMMAND_PHRASES: tuple[str, ...] = (
    "start obstacle detection",
    "detect obstacle",
    "obstacle detection",
    "recognize face",
    "recognize emotion",
    "start money detection",
    "money detection",
    "read text",
    "help me",
    "call help",
    "emergency mode",
    "navigation mode",
    "start navigation mode",
)
_ARABIC_VARIANTS: tuple[str, ...] = (
    "\u0627\u0642\u0631\u0623 \u0627\u0644\u0646\u0635",  # read text
    "\u0627\u0634\u063a\u0644 \u0627\u0643\u062a\u0634\u0627\u0641 \u0627\u0644\u0639\u0648\u0627\u0626\u0642",  # start obstacle detection
    "\u0627\u0633\u062a\u062f\u0639\u064a \u0645\u0633\u0627\u0639\u062f\u0629",  # call help
    "\u0646\u0645\u0637 \u0627\u0644\u0637\u0648\u0627\u0631\u0626",  # emergency mode
)
_BILINGUAL_VARIANTS: tuple[str, ...] = (
    "read text bel araby",
    "detect obstacle bel araby",
    "help me ya egb",
    "start navigation mode araby",
    "say yes ya egb",
    "say no ya egb",
)
_PHONETIC_VARIANTS: tuple[str, ...] = (
    "obsticle detection",
    "detect obsticle",
    "rekognize face",
    "rikognize face",
    "ay jee bee",
    "egb",
)
_STT_MISTAKE_VARIANTS: tuple[str, ...] = (
    "start obsticle",
    "obstacle detction",
    "reed text",
    "detect obstcles",
    "recognise face",
    "emergncy mode",
    "naviation mode",
)


def _normalize(value: str) -> str:
    return _WHITESPACE.sub(" ", str(value or "").strip())


def _dedupe_stable(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        normalized = _normalize(raw)
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return tuple(result)


@dataclass(frozen=True)
class PhraseHintSet:
    phrase_hint_set_id: str
    mode: str
    language_scope: str
    source_catalogs: tuple[str, ...]
    priority_order: tuple[str, ...]
    variant_types: tuple[str, ...]
    max_cloud_phrases: int
    max_strict_grammar_phrases: int
    phrases: tuple[str, ...]
    raw_user_content_present: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "phrase_hint_set_id": self.phrase_hint_set_id,
            "mode": self.mode,
            "language_scope": self.language_scope,
            "source_catalogs": self.source_catalogs,
            "priority_order": self.priority_order,
            "variant_types": self.variant_types,
            "max_cloud_phrases": self.max_cloud_phrases,
            "max_strict_grammar_phrases": self.max_strict_grammar_phrases,
            "phrases": self.phrases,
            "raw_user_content_present": self.raw_user_content_present,
        }


def _command_catalog_keywords(limit: int = 120) -> tuple[str, ...]:
    try:
        from core import parser as command_parser
    except Exception:  # noqa: BLE001
        return ()
    phrases: list[str] = []
    for entry in command_parser.COMMAND_CATALOG.values():
        for keyword in entry.keywords:
            phrases.append(_normalize(str(keyword)))
            if len(phrases) >= limit:
                return _dedupe_stable(phrases)
    return _dedupe_stable(phrases)


def _lexicon_command_phrases() -> tuple[str, ...]:
    try:
        return _dedupe_stable(load_command_lexicon().all_phrases())
    except Exception:  # noqa: BLE001
        return ()


def _command_priority_stream() -> tuple[str, ...]:
    prioritized: list[str] = []
    prioritized.extend(_SAFETY_CRITICAL_COMMANDS)
    prioritized.extend(_command_catalog_keywords())
    prioritized.extend(_ASSISTIVE_COMMAND_PHRASES)
    prioritized.extend(_ARABIC_VARIANTS)
    prioritized.extend(_BILINGUAL_VARIANTS)
    prioritized.extend(_PHONETIC_VARIANTS)
    prioritized.extend(_STT_MISTAKE_VARIANTS)
    prioritized.extend(_lexicon_command_phrases())
    return _dedupe_stable(prioritized)


def _mode_phrases(
    *,
    mode: str,
    closed_vocabulary_id: str | None,
    closed_choices: Sequence[str] | None,
) -> tuple[str, ...]:
    if mode == "wake":
        return _dedupe_stable(_WAKE_ALIASES)

    if mode == "confirmation":
        if closed_choices:
            return _dedupe_stable(closed_choices)
        return _dedupe_stable(closed_vocabulary_choices(closed_vocabulary_id or "confirmation.yes_no"))

    if mode == "onboarding":
        phrases: list[str] = list(closed_choices or ())
        if not phrases:
            for vocab_id in ("onboarding.language_choice", "onboarding.voice_choice", "onboarding.speed_choice"):
                phrases.extend(closed_vocabulary_choices(vocab_id))
        return _dedupe_stable(phrases)

    return _command_priority_stream()


def build_phrase_hint_set(
    *,
    mode: str,
    language_scope: str = "bilingual",
    closed_vocabulary_id: str | None = None,
    closed_choices: Sequence[str] | None = None,
) -> PhraseHintSet:
    normalized_mode = str(mode or "").strip().lower()
    if normalized_mode not in PHRASE_HINT_MODES:
        raise ValueError(f"Unsupported hint mode: {mode}")

    phrases = list(
        _mode_phrases(
            mode=normalized_mode,
            closed_vocabulary_id=closed_vocabulary_id,
            closed_choices=closed_choices,
        )
    )
    if normalized_mode == "command":
        source_catalogs = COMMAND_SOURCE_CATALOGS
        priority_order = COMMAND_PRIORITY_ORDER
        variant_types = ("canonical", "english", "arabic", "bilingual", "phonetic", "stt_mistake")
        phrase_hint_set_id = "command.default"
        phrases = list(_dedupe_stable(phrases[:DEFAULT_COMMAND_HINT_CAP]))
        max_cloud_phrases = DEFAULT_CLOUD_COMMAND_HINT_CAP
        max_strict_grammar_phrases = DEFAULT_COMMAND_HINT_CAP
    elif normalized_mode == "wake":
        source_catalogs = ("canonical_wake_aliases", "approved_safe_variants")
        priority_order = ("canonical_wake_aliases", "safe_variant_priority")
        variant_types = ("canonical", "english", "arabic", "bilingual", "phonetic", "stt_mistake")
        phrase_hint_set_id = "wake.default"
        phrases = list(_dedupe_stable(phrases[:DEFAULT_STRICT_WAKE_GRAMMAR_CAP]))
        max_cloud_phrases = DEFAULT_CLOUD_WAKE_HINT_CAP
        max_strict_grammar_phrases = DEFAULT_STRICT_WAKE_GRAMMAR_CAP
    else:
        source_catalogs = ("core.closed_vocabulary",)
        priority_order = ("closed_vocabulary_order",)
        variant_types = ("canonical", "english", "arabic", "bilingual")
        phrase_hint_set_id = (
            f"{normalized_mode}.{closed_vocabulary_id}"
            if closed_vocabulary_id
            else f"{normalized_mode}.default"
        )
        max_cloud_phrases = DEFAULT_CLOUD_COMMAND_HINT_CAP
        max_strict_grammar_phrases = DEFAULT_COMMAND_HINT_CAP

    return PhraseHintSet(
        phrase_hint_set_id=phrase_hint_set_id,
        mode=normalized_mode,
        language_scope=str(language_scope or "bilingual"),
        source_catalogs=tuple(source_catalogs),
        priority_order=tuple(priority_order),
        variant_types=tuple(variant_types),
        max_cloud_phrases=max_cloud_phrases,
        max_strict_grammar_phrases=max_strict_grammar_phrases,
        phrases=tuple(_dedupe_stable(phrases)),
        raw_user_content_present=False,
    )
