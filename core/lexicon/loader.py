"""Loader and validation for the command lexicon JSON catalog."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable

_WHITESPACE = re.compile(r"\s+")
_DEFAULT_LEXICON_PATH = Path(__file__).with_name("command_lexicon.json")
_ALLOWED_CATEGORIES = {"capability", "settings", "system"}
_ALLOWED_RISK_LEVELS = {"normal", "elevated", "protected"}


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", str(value or "")).strip().lower()
    return _WHITESPACE.sub(" ", normalized)


def _coerce_string_list(value: Any, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    result: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            result.append(text)
    return tuple(result)


@dataclass(frozen=True)
class LexiconPattern:
    intent_id: str
    pattern_id: str
    canonical: str
    when_any: tuple[str, ...]
    and_any: tuple[str, ...]


@dataclass(frozen=True)
class LexiconIntent:
    intent_id: str
    canonical: str
    category: str
    risk_level: str
    capability_id: str | None
    phrases: dict[str, tuple[str, ...]]
    patterns: tuple[LexiconPattern, ...]

    def all_phrases(self) -> tuple[str, ...]:
        phrases: list[str] = [self.canonical]
        for values in self.phrases.values():
            phrases.extend(values)
        return _dedupe(phrases)


@dataclass(frozen=True)
class CommandLexicon:
    version: int
    intents: dict[str, LexiconIntent]
    ambiguous_phrases: tuple[str, ...]

    def phrases_by_intent(self) -> dict[str, tuple[str, ...]]:
        return {intent_id: intent.all_phrases() for intent_id, intent in self.intents.items()}

    def parser_phrases_by_intent(self) -> dict[str, tuple[str, ...]]:
        result: dict[str, tuple[str, ...]] = {}
        for intent_id, intent in self.intents.items():
            phrases: list[str] = [intent.canonical]
            for group, values in intent.phrases.items():
                if group == "stt_mistakes":
                    continue
                phrases.extend(values)
            result[intent_id] = _dedupe(phrases)
        return result

    def aliases(self) -> tuple[tuple[str, str, str], ...]:
        aliases: list[tuple[str, str, str]] = []
        ambiguous = {_normalize_text(item) for item in self.ambiguous_phrases}
        for intent in self.intents.values():
            canonical_norm = _normalize_text(intent.canonical)
            for group, phrases in intent.phrases.items():
                if group == "en":
                    continue
                for phrase in phrases:
                    phrase_norm = _normalize_text(phrase)
                    if not phrase_norm or phrase_norm == canonical_norm or phrase_norm in ambiguous:
                        continue
                    aliases.append((phrase, intent.canonical, f"lexicon.{intent.intent_id}.{group}"))
        return tuple(aliases)

    def patterns(self) -> tuple[LexiconPattern, ...]:
        patterns: list[LexiconPattern] = []
        for intent in self.intents.values():
            patterns.extend(intent.patterns)
        return tuple(patterns)

    def all_phrases(self) -> tuple[str, ...]:
        phrases: list[str] = []
        for intent in self.intents.values():
            phrases.extend(intent.all_phrases())
        return _dedupe(phrases)


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        key = _normalize_text(text)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return tuple(result)


def _load_raw(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError as exc:
        raise ValueError(f"Command lexicon not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Command lexicon is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Command lexicon root must be an object")
    return payload


def _parse_pattern(intent_id: str, canonical: str, raw: Any, index: int) -> LexiconPattern:
    if not isinstance(raw, dict):
        raise ValueError(f"{intent_id}.patterns[{index}] must be an object")
    pattern_id = str(raw.get("id") or "").strip()
    if not pattern_id:
        raise ValueError(f"{intent_id}.patterns[{index}].id is required")
    pattern_canonical = str(raw.get("canonical") or canonical).strip()
    if not pattern_canonical:
        raise ValueError(f"{intent_id}.patterns[{index}].canonical is required")
    when_any = _coerce_string_list(raw.get("when_any"), field_name=f"{intent_id}.{pattern_id}.when_any")
    and_any = _coerce_string_list(raw.get("and_any"), field_name=f"{intent_id}.{pattern_id}.and_any")
    if not when_any and not and_any:
        raise ValueError(f"{intent_id}.{pattern_id} must define when_any or and_any")
    return LexiconPattern(
        intent_id=intent_id,
        pattern_id=pattern_id,
        canonical=pattern_canonical,
        when_any=when_any,
        and_any=and_any,
    )


def _parse_intent(intent_id: str, raw: Any) -> LexiconIntent:
    if not isinstance(raw, dict):
        raise ValueError(f"{intent_id} must be an object")
    canonical = str(raw.get("canonical") or "").strip()
    category = str(raw.get("category") or "").strip()
    risk_level = str(raw.get("risk_level") or "").strip()
    if not canonical:
        raise ValueError(f"{intent_id}.canonical is required")
    if category not in _ALLOWED_CATEGORIES:
        raise ValueError(f"{intent_id}.category must be one of {sorted(_ALLOWED_CATEGORIES)}")
    if risk_level not in _ALLOWED_RISK_LEVELS:
        raise ValueError(f"{intent_id}.risk_level must be one of {sorted(_ALLOWED_RISK_LEVELS)}")

    raw_phrases = raw.get("phrases")
    if not isinstance(raw_phrases, dict):
        raise ValueError(f"{intent_id}.phrases must be an object")
    phrases = {
        str(group): _coerce_string_list(values, field_name=f"{intent_id}.phrases.{group}")
        for group, values in raw_phrases.items()
    }
    if not any(phrases.values()):
        raise ValueError(f"{intent_id}.phrases must contain at least one phrase")

    raw_patterns = raw.get("patterns", [])
    if not isinstance(raw_patterns, list):
        raise ValueError(f"{intent_id}.patterns must be a list")
    patterns = tuple(_parse_pattern(intent_id, canonical, item, index) for index, item in enumerate(raw_patterns))

    capability_id = raw.get("capability_id")
    return LexiconIntent(
        intent_id=intent_id,
        canonical=canonical,
        category=category,
        risk_level=risk_level,
        capability_id=str(capability_id).strip() if capability_id is not None else None,
        phrases=phrases,
        patterns=patterns,
    )


def _validate_collisions(lexicon: CommandLexicon) -> None:
    owners: dict[str, tuple[str, str]] = {}
    ambiguous = {_normalize_text(item) for item in lexicon.ambiguous_phrases}
    for intent in lexicon.intents.values():
        for phrase in intent.all_phrases():
            key = _normalize_text(phrase)
            if not key or key in ambiguous:
                continue
            previous = owners.get(key)
            if previous and previous[0] != intent.intent_id:
                raise ValueError(
                    "Command lexicon phrase collision: "
                    f"{phrase!r} belongs to both {previous[0]} and {intent.intent_id}"
                )
            owners[key] = (intent.intent_id, phrase)


def parse_command_lexicon(payload: dict[str, Any]) -> CommandLexicon:
    version = int(payload.get("version") or 1)
    raw_intents = payload.get("intents")
    if not isinstance(raw_intents, dict) or not raw_intents:
        raise ValueError("Command lexicon requires a non-empty intents object")
    ambiguous_phrases = _coerce_string_list(payload.get("ambiguous_phrases", []), field_name="ambiguous_phrases")
    intents = {str(intent_id): _parse_intent(str(intent_id), raw) for intent_id, raw in raw_intents.items()}
    lexicon = CommandLexicon(version=version, intents=intents, ambiguous_phrases=ambiguous_phrases)
    _validate_collisions(lexicon)
    return lexicon


@lru_cache(maxsize=4)
def load_command_lexicon(path: str | Path | None = None) -> CommandLexicon:
    lexicon_path = Path(path) if path is not None else _DEFAULT_LEXICON_PATH
    return parse_command_lexicon(_load_raw(lexicon_path))
