"""Command transcript normalization and canonicalization helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Sequence

from core.command_models import CommandPostProcessingOutcome

_ARABIC_RANGE_PATTERN = re.compile(r"[\u0600-\u06FF]")
_ENGLISH_RANGE_PATTERN = re.compile(r"[a-zA-Z]")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_PUNCTUATION_PATTERN = re.compile(r"[^\w\s\u0600-\u06FF]")


@dataclass(frozen=True)
class _SubstitutionRule:
    pattern: re.Pattern[str]
    replacement: str
    rule_id: str


_SUBSTITUTION_RULES: tuple[_SubstitutionRule, ...] = (
    _SubstitutionRule(re.compile(r"\breed\b"), "read", "en.read_text.reed_to_read"),
    _SubstitutionRule(re.compile(r"\btxt\b"), "text", "en.read_text.txt_to_text"),
    _SubstitutionRule(re.compile(r"\bobsticle\b"), "obstacle", "en.obstacle.obsticle_to_obstacle"),
    _SubstitutionRule(re.compile(r"\brecgonize\b"), "recognize", "en.recognize.recgonize_to_recognize"),
    _SubstitutionRule(re.compile(r"\bo\s*c\s*r\b"), "ocr", "en.ocr.spaced_to_token"),
    _SubstitutionRule(re.compile(r"\bengilsh\b"), "english", "en.language.engilsh_to_english"),
    _SubstitutionRule(re.compile(r"\baraby\b"), "arabic", "en.language.araby_to_arabic"),
    _SubstitutionRule(re.compile(r"\bانجليش\b"), "انجليزي", "ar.language.anglish_to_english"),
)

_CANONICAL_ALIASES: dict[str, tuple[str, str]] = {
    "switch language to english": ("switch to english", "en.language.switch_word_order"),
    "switch language to arabic": ("switch to arabic", "en.language.switch_word_order"),
    "switch language to arab": ("switch to arabic", "en.language.switch_word_order_arab_to_arabic"),
    "set language english": ("switch to english", "en.language.set_to_switch"),
    "set language arabic": ("switch to arabic", "en.language.set_to_switch"),
    "set language arab": ("switch to arabic", "en.language.set_to_switch_arab_to_arabic"),
    "change language to arab": ("switch to arabic", "en.language.change_to_switch_arab_to_arabic"),
    "check system status": ("get status", "en.status.check_to_get"),
    "status please": ("get status", "en.status.please_to_get"),
    "put on the obstacle detection please": (
        "start obstacle detection",
        "en.obstacle.put_on_please_to_start",
    ),
    "put on obstacle detection please": (
        "start obstacle detection",
        "en.obstacle.put_on_please_to_start",
    ),
    "put en obstacle detection please": (
        "start obstacle detection",
        "en.obstacle.put_en_to_put_on",
    ),
    "put on obstacle detection": (
        "start obstacle detection",
        "en.obstacle.put_on_to_start",
    ),
    "run obstacle detection": (
        "start obstacle detection",
        "en.obstacle.run_to_start",
    ),
    "run obstacle detection please": (
        "start obstacle detection",
        "en.obstacle.run_please_to_start",
    ),
    "rung obstacle detection": (
        "start obstacle detection",
        "en.obstacle.rung_to_run",
    ),
    "runn obstacle detection": (
        "start obstacle detection",
        "en.obstacle.runn_to_run",
    ),
    "rusne obstacle detection": (
        "start obstacle detection",
        "en.obstacle.rusne_to_run",
    ),
    "banana obstacle detection": (
        "start obstacle detection",
        "en.obstacle.banana_to_put_on",
    ),
    "rana obstacle detection please": (
        "start obstacle detection",
        "en.obstacle.rana_to_run",
    ),
    "rannoch obstacle detection please": (
        "start obstacle detection",
        "en.obstacle.rannoch_to_run",
    ),
    "disable obd": ("disable obstacle detection", "en.obstacle.obd_to_obstacle"),
    "disable obi": ("disable obstacle detection", "en.obstacle.obi_to_obstacle"),
    "obstacle detection": ("start obstacle detection", "en.obstacle.bare_to_start"),
    "obstacle detection please": (
        "start obstacle detection",
        "en.obstacle.bare_please_to_start",
    ),
    "obstacle collection please": (
        "start obstacle detection",
        "en.obstacle.collection_to_detection",
    ),
    "obstacle fiction please": (
        "start obstacle detection",
        "en.obstacle.fiction_to_detection",
    ),
    "obstacle section please": (
        "start obstacle detection",
        "en.obstacle.section_to_detection",
    ),
    "obstacle debt": ("start obstacle detection", "en.obstacle.debt_to_detection"),
    "obstacle det": ("start obstacle detection", "en.obstacle.det_to_detection"),
    "money": ("start money detection", "en.money.bare_to_start"),
    "money please": ("start money detection", "en.money.bare_please_to_start"),
    "money detection": ("start money detection", "en.money.bare_detection_to_start"),
    "money detection please": (
        "start money detection",
        "en.money.bare_detection_please_to_start",
    ),
    "run money detection": ("start money detection", "en.money.run_to_start"),
    "run the money detection": ("start money detection", "en.money.run_to_start"),
    "run a money detection": ("start money detection", "en.money.run_to_start"),
    "run the money debt": ("start money detection", "en.money.debt_to_detection"),
    "rung the money detection": ("start money detection", "en.money.rung_to_run"),
    "run the monie detection": ("start money detection", "en.money.monie_to_money"),
    "run the munny detection": ("start money detection", "en.money.munny_to_money"),
    "put on money detection": ("start money detection", "en.money.put_on_to_start"),
    "put on the money detection": ("start money detection", "en.money.put_on_to_start"),
    "put on the monie detection": ("start money detection", "en.money.monie_to_money"),
    "ماني": ("start money detection", "ar.money.bare_to_start"),
    "ماني ديتكشن": ("start money detection", "ar.money.detection_to_start"),
    "\u0631\u0646\u0627 \u0645\u0627\u0646\u064a \u062f\u064a\u062a\u0643\u0634\u0646": (
        "start money detection",
        "ar.money.runa_detection_to_start",
    ),
    "emot": ("recognize emotion", "en.emotion.short_to_recognize"),
    "emotion": ("recognize emotion", "en.emotion.bare_to_recognize"),
    "emotion please": ("recognize emotion", "en.emotion.bare_please_to_recognize"),
    "run the fish recognition": ("face recognition", "en.face.fish_to_face"),
    "turn the fish recognition": ("face recognition", "en.face.fish_to_face"),
    "rung the fish recognition": ("face recognition", "en.face.fish_to_face"),
    "\u0631\u0646\u0627 \u0641\u064a\u0633 \u0643\u0648\u0631\u0646\u064a\u0634": (
        "face recognition",
        "ar.face.corniche_to_recognition",
    ),
    "ocr please": ("start ocr", "en.ocr.please_to_start"),
    "enable ocr please": ("enable ocr", "en.ocr.enable_please"),
    "start ocr please": ("start ocr", "en.ocr.start_please"),
    "text detection": ("start ocr", "en.ocr.text_detection_to_start"),
    "run text detection": ("start ocr", "en.ocr.text_detection_to_start"),
    "run a text detection": ("start ocr", "en.ocr.text_detection_to_start"),
    "put on text detection": ("start ocr", "en.ocr.text_detection_to_start"),
    "put on a text detection": ("start ocr", "en.ocr.text_detection_to_start"),
    "run a ticket": ("start ocr", "en.ocr.ticket_to_text_detection"),
    "run a ticket detection": ("start ocr", "en.ocr.ticket_to_text_detection"),
    "put on a ticket to the diction": ("start ocr", "en.ocr.ticket_diction_to_text_detection"),
    "put on a tickets to the diction": ("start ocr", "en.ocr.ticket_diction_to_text_detection"),
    "take us to detection": ("start ocr", "en.ocr.take_us_to_text_detection"),
    "\u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u064a": (
        "start ocr",
        "ar.ocr.incomplete_text_recognition_to_start",
    ),
    "\u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u062a\u0639\u0631\u0641": (
        "start ocr",
        "ar.ocr.incomplete_text_recognition_to_start",
    ),
    "\u0634\u063a\u0644 \u0627\u0644\u062a\u0639\u0631\u0641": (
        "start ocr",
        "ar.ocr.casual_incomplete_recognition_to_start",
    ),
    "\u0634\u063a\u0644 \u0644\u064a \u0627\u0644\u062a\u0639\u0631\u0641": (
        "start ocr",
        "ar.ocr.casual_incomplete_recognition_to_start",
    ),
    "\u0634\u063a\u0644 \u0644\u064a \u0627\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u064a": (
        "start ocr",
        "ar.ocr.casual_text_recognition_to_start",
    ),
    "\u0634\u063a\u0644 \u0627\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u064a": (
        "start ocr",
        "ar.ocr.casual_text_recognition_to_start",
    ),
    "\u062a\u0639\u0631\u0641 \u0639\u0644\u064a \u0627\u0644\u0646\u0635\u0648\u0635": (
        "start ocr",
        "ar.ocr.text_recognition_to_start",
    ),
    "\u0627\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u064a \u0627\u0644\u0646\u0635\u0648\u0635": (
        "start ocr",
        "ar.ocr.text_recognition_to_start",
    ),
    "\u0627\u0648 \u0633\u064a \u0627\u0631": ("start ocr", "ar.ocr.letters_to_start"),
    "\u0627\u0648 \u0633\u064a \u0627\u0631 \u0628\u0644\u064a": ("start ocr", "ar.ocr.letters_please_to_start"),
    "\u0627\u0646\u064a\u0628\u0644 \u0627\u0648 \u0633\u064a \u0627\u0631": ("enable ocr", "ar.ocr.enable_letters"),
    "\u0627\u0646\u064a\u0628\u0644 au \u0633\u064a \u0627\u0631": ("enable ocr", "ar.ocr.enable_letters_mixed"),
    "yes please": ("yes", "en.confirm.yes_please_to_yes"),
    "no thanks": ("no", "en.confirm.no_thanks_to_no"),
    "نعم من فضلك": ("نعم", "ar.confirm.yes_please_to_yes"),
    "لا شكرا": ("لا", "ar.confirm.no_thanks_to_no"),
}

_CONFUSION_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("mail", "male", "voice.male_mail"),
    ("female voice", "female", "voice.female_phrase"),
    ("english language", "english", "language.english_phrase"),
    ("arabic language", "arabic", "language.arabic_phrase"),
)

_WAKE_PREFIX_ALIASES: tuple[str, ...] = (
    "hi egb",
    "hello egb",
    "hi agency",
    "hi hgb",
    "marhaba",
    "hay egy bee",
)

_AR_START_TERMS: tuple[str, ...] = (
    "\u0627\u0628\u062f\u0627",
    "\u0627\u0628\u062f\u0623",
    "\u0627\u0641\u062a\u062d",
    "\u062a\u0634\u063a\u064a\u0644",
    "\u062a\u0641\u0639\u064a\u0644",
    "\u0641\u0639\u0644",
    "\u0634\u063a\u0644",
)
_AR_STOP_TERMS: tuple[str, ...] = (
    "\u0627\u0637\u0641\u064a",
    "\u0627\u0642\u0641\u0644",
    "\u0627\u064a\u0642\u0627\u0641",
    "\u0627\u0648\u0642\u0641",
    "\u062a\u0639\u0637\u064a\u0644",
    "\u0639\u0637\u0644",
    "\u0648\u0642\u0641",
)
_AR_RECOGNITION_TERMS: tuple[str, ...] = (
    "\u0627\u0644\u062a\u0639\u0631\u0641",
    "\u0627\u062a\u0639\u0631\u0641",
    "\u062a\u0639\u0631\u0641",
    "\u0627\u0639\u0631\u0641",
    "\u0627\u0643\u062a\u0634\u0641",
)
_AR_TEXT_TERMS: tuple[str, ...] = (
    "\u0627\u0644\u0646\u0635",
    "\u0627\u0644\u0646\u0635\u0648\u0635",
    "\u0643\u062a\u0627\u0628\u0647",
    "\u0642\u0631\u0627\u0621\u0647",
    "\u0646\u0635",
    "\u0646\u0635\u0648\u0635",
    "\u0627\u0648 \u0633\u064a \u0627\u0631",
)
_AR_FACE_TERMS: tuple[str, ...] = (
    "\u0627\u0644\u0648\u062c\u0647",
    "\u0627\u0644\u0648\u062c\u0648\u0647",
    "\u0627\u0644\u0648\u0634",
    "\u0627\u0644\u0648\u0634\u0648\u0634",
    "\u0648\u062c\u0647",
    "\u0648\u062c\u0648\u0647",
    "\u0648\u0634",
    "\u0641\u064a\u0633",
)
_AR_EMOTION_TERMS: tuple[str, ...] = (
    "\u0627\u0644\u0645\u0634\u0627\u0639\u0631",
    "\u0627\u064a\u0645\u0648\u0634\u0646",
    "\u0627\u0644\u0639\u0627\u0637\u0641\u0647",
    "\u0627\u0644\u0645\u0648\u062f",
    "\u0645\u0634\u0627\u0639\u0631",
)
_AR_MONEY_TERMS: tuple[str, ...] = (
    "\u0627\u0644\u0641\u0644\u0648\u0633",
    "\u0627\u0644\u0646\u0642\u0648\u062f",
    "\u0627\u0644\u0639\u0645\u0644\u0647",
    "\u0627\u0644\u0645\u0627\u0646\u064a",
    "\u0641\u0644\u0648\u0633",
    "\u0646\u0642\u0648\u062f",
    "\u0639\u0645\u0644\u0647",
    "\u0645\u0627\u0646\u064a",
)
_AR_OBSTACLE_TERMS: tuple[str, ...] = (
    "\u0627\u0644\u0639\u0648\u0627\u0626\u0642",
    "\u0627\u0644\u062d\u0648\u0627\u062c\u0632",
    "\u0627\u0648\u0628\u0633\u062a\u0627\u0643\u0644",
    "\u0639\u0648\u0627\u0626\u0642",
    "\u062d\u0648\u0627\u062c\u0632",
)


def _normalize_surface_text(text: str) -> str:
    cleaned = str(text or "").strip().lower()
    cleaned = (
        cleaned.replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ى", "ي")
        .replace("ة", "ه")
    )
    cleaned = _PUNCTUATION_PATTERN.sub(" ", cleaned)
    cleaned = _WHITESPACE_PATTERN.sub(" ", cleaned)
    return cleaned.strip()


def _language_hints(normalized_text: str) -> tuple[str, ...]:
    hints: list[str] = []
    has_ar = bool(_ARABIC_RANGE_PATTERN.search(normalized_text))
    has_en = bool(_ENGLISH_RANGE_PATTERN.search(normalized_text))
    if has_ar:
        hints.append("ar")
    if has_en:
        hints.append("en")
    if has_ar and has_en:
        hints.append("mixed")
    return tuple(hints)


def _resolve_confusion_pair(text: str) -> tuple[str, str | None]:
    for noisy, canonical, pair_id in _CONFUSION_PAIRS:
        if text == noisy:
            return canonical, pair_id
    return text, None


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _resolve_pattern_alias(text: str) -> tuple[str, str] | None:
    if not _ARABIC_RANGE_PATTERN.search(text):
        return None

    has_start = _contains_any(text, _AR_START_TERMS)
    has_stop = _contains_any(text, _AR_STOP_TERMS)
    has_recognition = _contains_any(text, _AR_RECOGNITION_TERMS)

    if _contains_any(text, _AR_MONEY_TERMS):
        if has_stop:
            return "disable money detection", "ar.money.pattern_disable"
        if has_start or has_recognition:
            return "start money detection", "ar.money.pattern_enable"

    if _contains_any(text, _AR_OBSTACLE_TERMS):
        if has_stop:
            return "disable obstacle detection", "ar.obstacle.pattern_disable"
        if has_start or has_recognition:
            return "start obstacle detection", "ar.obstacle.pattern_enable"

    if _contains_any(text, _AR_EMOTION_TERMS) and (has_start or has_recognition):
        return "recognize emotion", "ar.emotion.pattern_recognition"

    if _contains_any(text, _AR_TEXT_TERMS) and (has_start or has_recognition):
        return "start ocr", "ar.ocr.pattern_text_recognition_to_start"

    if _contains_any(text, _AR_FACE_TERMS) and (has_start or has_recognition):
        return "face recognition", "ar.face.pattern_recognition"

    return None


def _strip_wake_prefix(text: str) -> tuple[str, bool]:
    normalized = _normalize_surface_text(text)
    if not normalized:
        return "", False
    for wake_alias in _WAKE_PREFIX_ALIASES:
        if normalized == wake_alias:
            return "", True
        prefix = f"{wake_alias} "
        if normalized.startswith(prefix):
            return normalized[len(prefix) :].strip(), True
    return normalized, False


def _select_closed_vocabulary_option(
    normalized_text: str,
    closed_vocabulary: Sequence[str],
) -> tuple[str | None, float]:
    candidates = [_normalize_surface_text(item) for item in closed_vocabulary if _normalize_surface_text(item)]
    if not candidates:
        return None, 0.0
    if normalized_text in candidates:
        return normalized_text, 1.0
    best_match: str | None = None
    best_score = 0.0
    for candidate in candidates:
        ratio = SequenceMatcher(None, normalized_text, candidate).ratio()
        if ratio > best_score:
            best_score = ratio
            best_match = candidate
    return best_match, best_score


def process_command_transcript(
    source_transcript: str,
    *,
    alternative_transcripts: Sequence[str] | None = None,
    language_hints: Sequence[str] | None = None,
    dictionary_mode: str = "command_inventory",
    closed_vocabulary_id: str | None = None,
    closed_vocabulary: Sequence[str] | None = None,
) -> CommandPostProcessingOutcome:
    """Normalize noisy transcript text into parser-ready canonical command text."""
    source = str(source_transcript or "")
    source_normalized = _normalize_surface_text(source)
    mode = str(dictionary_mode or "command_inventory").strip().lower()

    if not source_normalized:
        return CommandPostProcessingOutcome(
            source_transcript=source,
            normalized_transcript="",
            canonical_command_text="",
            substitution_ids=(),
            language_hints=tuple(language_hints or ()),
            dictionary_mode=mode,
            closed_vocabulary_id=closed_vocabulary_id,
            ambiguity_flags=("empty_transcript",),
            post_processing_status="rejected",
        )

    normalized, wake_prefix_removed = _strip_wake_prefix(source_normalized)
    substitution_ids: list[str] = []
    if wake_prefix_removed:
        substitution_ids.append("wake.prefix_removed")
    for rule in _SUBSTITUTION_RULES:
        updated = rule.pattern.sub(rule.replacement, normalized)
        if updated != normalized:
            normalized = updated
            substitution_ids.append(rule.rule_id)

    alias_entry = _CANONICAL_ALIASES.get(normalized)
    if alias_entry is None:
        alias_entry = _resolve_pattern_alias(normalized)
    if alias_entry is not None:
        normalized = alias_entry[0]
        substitution_ids.append(alias_entry[1])

    normalized, confusion_pair_id = _resolve_confusion_pair(normalized)

    normalized = _normalize_surface_text(normalized)
    ambiguity_flags: list[str] = []
    alt_values = [_normalize_surface_text(item) for item in list(alternative_transcripts or ())]
    distinct_alt_values = {item for item in alt_values if item}
    if len(distinct_alt_values) > 1:
        ambiguity_flags.append("conflicting_alternatives")

    canonical_text = normalized
    if " and " in canonical_text and _ARABIC_RANGE_PATTERN.search(canonical_text):
        ambiguity_flags.append("mixed_language_connector")

    if mode == "closed_choice":
        options = list(closed_vocabulary or ())
        match, score = _select_closed_vocabulary_option(canonical_text, options)
        if match is not None and score >= 0.78:
            canonical_text = match
        else:
            ambiguity_flags.append("out_of_closed_vocabulary")
            return CommandPostProcessingOutcome(
                source_transcript=source,
                normalized_transcript=normalized,
                canonical_command_text="",
                substitution_ids=tuple(substitution_ids),
                language_hints=tuple(language_hints or ()) or _language_hints(normalized),
                dictionary_mode="closed_choice",
                closed_vocabulary_id=closed_vocabulary_id or "closed_choice.default",
                confusion_pair_id=confusion_pair_id,
                ambiguity_flags=tuple(ambiguity_flags),
                post_processing_status="constrained_retry",
            )

    hints = tuple(language_hints or ()) or _language_hints(canonical_text)
    if not canonical_text:
        status = "rejected"
        ambiguity_flags.append("empty_after_normalization")
    elif canonical_text != source_normalized or substitution_ids or confusion_pair_id:
        status = "normalized"
    else:
        status = "unchanged"

    return CommandPostProcessingOutcome(
        source_transcript=source,
        normalized_transcript=normalized,
        canonical_command_text=canonical_text,
        substitution_ids=tuple(substitution_ids),
        language_hints=hints,
        dictionary_mode=mode,
        closed_vocabulary_id=closed_vocabulary_id,
        confusion_pair_id=confusion_pair_id,
        ambiguity_flags=tuple(ambiguity_flags),
        post_processing_status=status,
    )


def canonicalize_command_text(
    transcript: str,
    *,
    alternative_transcripts: Sequence[str] | None = None,
    language_hints: Sequence[str] | None = None,
) -> str:
    outcome = process_command_transcript(
        transcript,
        alternative_transcripts=alternative_transcripts,
        language_hints=language_hints,
    )
    return outcome.canonical_command_text
