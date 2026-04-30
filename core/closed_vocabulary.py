"""Shared closed-vocabulary registry for guided dialog turns."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable

_WHITESPACE_PATTERN = re.compile(r"\s+")
_PUNCT_PATTERN = re.compile(r"[^\w\s\u0600-\u06FF]")


@dataclass(frozen=True)
class ClosedVocabularyOption:
    option_id: str
    canonical_value: str
    persisted_value: str
    alias_tokens: tuple[str, ...]
    requires_confirmation: bool = False


@dataclass(frozen=True)
class ClosedVocabularyContext:
    closed_vocabulary_id: str
    flow_type: str
    usage_modes: tuple[str, ...]
    allow_mixed_language_aliases: bool
    global_safety_preemption_only: bool
    retry_limit: int
    safe_fallback_strategy: str
    options: tuple[ClosedVocabularyOption, ...]


@dataclass(frozen=True)
class ClosedVocabularyMatch:
    option_id: str
    canonical_value: str
    persisted_value: str
    matched_alias: str
    confidence: float


_ALIASES: dict[str, str] = {
    "confirmation.yes_no": "confirmation.yes_no_cancel",
    "onboarding.default": "onboarding.language_choice",
}

_GLOBAL_SAFETY_ALIASES: tuple[str, ...] = (
    "stop",
    "cancel",
    "emergency",
    "shutdown",
    "قف",
    "توقف",
    "الغاء",
    "إلغاء",
)


def _normalize_text(value: str) -> str:
    normalized = str(value or "").strip().lower()
    normalized = (
        normalized.replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ى", "ي")
        .replace("ة", "ه")
    )
    normalized = _PUNCT_PATTERN.sub(" ", normalized)
    normalized = _WHITESPACE_PATTERN.sub(" ", normalized)
    return normalized.strip()


def _option(*, option_id: str, canonical: str, aliases: Iterable[str], persisted: str | None = None) -> ClosedVocabularyOption:
    normalized_aliases = tuple(
        dict.fromkeys(_normalize_text(alias) for alias in aliases if _normalize_text(alias))
    )
    return ClosedVocabularyOption(
        option_id=option_id,
        canonical_value=_normalize_text(canonical),
        persisted_value=str(persisted or canonical),
        alias_tokens=normalized_aliases,
    )


def _build_registry() -> dict[str, ClosedVocabularyContext]:
    return {
        "confirmation.yes_no_cancel": ClosedVocabularyContext(
            closed_vocabulary_id="confirmation.yes_no_cancel",
            flow_type="confirmation",
            usage_modes=("confirmation",),
            allow_mixed_language_aliases=True,
            global_safety_preemption_only=True,
            retry_limit=1,
            safe_fallback_strategy="graceful_exit",
            options=(
                _option(
                    option_id="affirmative",
                    canonical="yes",
                    aliases=("yes", "yes please", "okay", "نعم", "ايوه", "تمام"),
                    persisted="affirmative",
                ),
                _option(
                    option_id="negative",
                    canonical="no",
                    aliases=("no", "nope", "لا", "لأ"),
                    persisted="negative",
                ),
                _option(
                    option_id="cancel",
                    canonical="cancel",
                    aliases=("cancel", "stop", "الغاء", "إلغاء"),
                    persisted="cancel",
                ),
            ),
        ),
        "onboarding.language_choice": ClosedVocabularyContext(
            closed_vocabulary_id="onboarding.language_choice",
            flow_type="onboarding",
            usage_modes=("onboarding",),
            allow_mixed_language_aliases=True,
            global_safety_preemption_only=False,
            retry_limit=2,
            safe_fallback_strategy="keep_default",
            options=(
                _option(
                    option_id="arabic",
                    canonical="arabic",
                    aliases=("arabic", "ar", "عربي", "العربيه"),
                    persisted="ar-EG",
                ),
                _option(
                    option_id="english",
                    canonical="english",
                    aliases=("english", "en", "انجليزي", "انجلش"),
                    persisted="en-US",
                ),
            ),
        ),
        "onboarding.voice_choice": ClosedVocabularyContext(
            closed_vocabulary_id="onboarding.voice_choice",
            flow_type="onboarding",
            usage_modes=("onboarding",),
            allow_mixed_language_aliases=True,
            global_safety_preemption_only=False,
            retry_limit=2,
            safe_fallback_strategy="keep_last_confirmed",
            options=(
                _option(
                    option_id="male",
                    canonical="male",
                    aliases=("male", "mail", "ذكر", "راجل", "ميل", "مايل"),
                    persisted="male",
                ),
                _option(
                    option_id="female",
                    canonical="female",
                    aliases=(
                        "female",
                        "femail",
                        "femal",
                        "انثي",
                        "انثى",
                        "انثه",
                        "بنت",
                        "ست",
                        "فيميل",
                        "في ميل",
                        "فيمايل",
                    ),
                    persisted="female",
                ),
            ),
        ),
        "onboarding.speed_choice": ClosedVocabularyContext(
            closed_vocabulary_id="onboarding.speed_choice",
            flow_type="onboarding",
            usage_modes=("onboarding",),
            allow_mixed_language_aliases=True,
            global_safety_preemption_only=False,
            retry_limit=2,
            safe_fallback_strategy="keep_default",
            options=(
                _option(
                    option_id="normal",
                    canonical="normal",
                    aliases=("normal", "norman", "default", "regular", "عادي", "طبيعي", "نورمال"),
                    persisted="1.0",
                ),
                _option(
                    option_id="fast",
                    canonical="fast",
                    aliases=("fast", "faster", "سريع", "اسرع"),
                    persisted="1.35",
                ),
                _option(
                    option_id="slow",
                    canonical="slow",
                    aliases=("slow", "slower", "بطيء", "ابطأ"),
                    persisted="0.85",
                ),
            ),
        ),
        "command.retry_help": ClosedVocabularyContext(
            closed_vocabulary_id="command.retry_help",
            flow_type="recovery",
            usage_modes=("command", "confirmation"),
            allow_mixed_language_aliases=True,
            global_safety_preemption_only=False,
            retry_limit=2,
            safe_fallback_strategy="graceful_exit",
            options=(
                _option(
                    option_id="retry",
                    canonical="retry",
                    aliases=("retry", "repeat", "try again", "كرر", "اعاده"),
                    persisted="retry",
                ),
                _option(
                    option_id="help",
                    canonical="help",
                    aliases=("help", "options", "مساعده", "ساعدني"),
                    persisted="help",
                ),
                _option(
                    option_id="cancel",
                    canonical="cancel",
                    aliases=("cancel", "stop", "الغاء", "إلغاء"),
                    persisted="cancel",
                ),
            ),
        ),
    }


_REGISTRY: dict[str, ClosedVocabularyContext] = _build_registry()


def resolve_closed_vocabulary_id(vocabulary_id: str | None) -> str | None:
    key = str(vocabulary_id or "").strip().lower()
    if not key:
        return None
    return _ALIASES.get(key, key)


def closed_vocabulary_context(vocabulary_id: str | None) -> ClosedVocabularyContext | None:
    resolved = resolve_closed_vocabulary_id(vocabulary_id)
    if resolved is None:
        return None
    return _REGISTRY.get(resolved)


def closed_vocabulary_choices(vocabulary_id: str | None) -> tuple[str, ...]:
    context = closed_vocabulary_context(vocabulary_id)
    if context is None:
        return ()
    values: list[str] = []
    for option in context.options:
        values.extend(option.alias_tokens)
    return tuple(dict.fromkeys(values))


def is_global_safety_preemption(utterance: str) -> bool:
    normalized = _normalize_text(utterance)
    if not normalized:
        return False
    return any(alias in normalized for alias in _GLOBAL_SAFETY_ALIASES)


def match_closed_vocabulary(
    *,
    utterance: str,
    vocabulary_id: str | None,
    minimum_similarity: float = 0.78,
) -> ClosedVocabularyMatch | None:
    context = closed_vocabulary_context(vocabulary_id)
    if context is None:
        return None
    normalized = _normalize_text(utterance)
    if not normalized:
        return None

    best_option: ClosedVocabularyOption | None = None
    best_alias: str | None = None
    best_score = 0.0
    for option in context.options:
        for alias in option.alias_tokens:
            if normalized == alias:
                return ClosedVocabularyMatch(
                    option_id=option.option_id,
                    canonical_value=option.canonical_value,
                    persisted_value=option.persisted_value,
                    matched_alias=alias,
                    confidence=1.0,
                )
            score = SequenceMatcher(None, normalized, alias).ratio()
            if score > best_score:
                best_score = score
                best_option = option
                best_alias = alias

    if best_option is None or best_alias is None or best_score < float(minimum_similarity):
        return None

    return ClosedVocabularyMatch(
        option_id=best_option.option_id,
        canonical_value=best_option.canonical_value,
        persisted_value=best_option.persisted_value,
        matched_alias=best_alias,
        confidence=float(best_score),
    )
