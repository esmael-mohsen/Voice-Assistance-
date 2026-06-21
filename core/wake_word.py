"""Wake word and interrupt phrase normalization helpers."""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum
from functools import lru_cache
from typing import Any, Callable, Iterable, Mapping

try:
    import speech_recognition as sr
except ModuleNotFoundError:  # pragma: no cover - lean test environments
    sr = None

CANONICAL_WAKE_PHRASES: tuple[str, str] = ("hi egb", "\u0645\u0631\u062d\u0628\u0627")


class WakeAction(str, Enum):
    START = "start"
    STOP = "stop"


@dataclass(frozen=True)
class WakeResult:
    action: WakeAction
    phrase: str


class WakeDetectionProfile(str, Enum):
    STRICT = "strict"
    BALANCED = "balanced"
    DEVELOPMENT = "development"


@dataclass(frozen=True)
class WakeProfileConfig:
    decision_threshold: float
    exact_weight: float
    prefix_weight: float
    token_overlap_weight: float
    subsequence_weight: float
    compact_weight: float
    greeting_weight: float
    bigram_weight: float
    fuzzy_weight: float
    missing_greeting_penalty: float
    fuzzy_gate_min: float


@dataclass(frozen=True)
class WakeAliasSpec:
    raw_phrase: str
    normalized_phrase: str
    compact_phrase: str
    tokens: tuple[str, ...]
    token_set: frozenset[str]
    bigrams: frozenset[str]
    requires_greeting: bool = False
    thresholds: Mapping[str, float] | None = None


@dataclass(frozen=True)
class WakeScore:
    alias: str
    total_score: float
    decision_threshold: float
    accepted: bool
    component_scores: dict[str, float]
    greeting_gate_passed: bool


@dataclass(frozen=True)
class WakeDetectionDecision:
    accepted: bool
    normalized_phrase: str
    profile: str
    matched_alias: str | None
    best_score: float
    decision_threshold: float
    component_scores: dict[str, float]
    greeting_gate_passed: bool


@dataclass(frozen=True)
class WakeTelemetrySnapshot:
    attempts: int
    accepts: int
    rejects: int
    false_accepts: int
    false_rejects: int
    false_accept_rate: float
    false_reject_rate: float
    last_score: float
    last_profile: str
    last_alias: str | None


@dataclass(frozen=True)
class InterruptMatch:
    signal_type: str
    normalized_phrase: str
    matched_vocabulary_ids: tuple[str, ...]


INTERRUPT_VOCABULARY: tuple[dict[str, object], ...] = (
    {
        "vocabulary_id": "interrupt-stop-en",
        "signal_type": "stop",
        "language_scope": "en",
        "phrase_variants": ("stop", "stop now"),
    },
    {
        "vocabulary_id": "interrupt-cancel-en",
        "signal_type": "cancel",
        "language_scope": "en",
        "phrase_variants": ("cancel",),
    },
    {
        "vocabulary_id": "interrupt-emergency-en",
        "signal_type": "emergency",
        "language_scope": "en",
        "phrase_variants": ("emergency",),
    },
    {
        "vocabulary_id": "interrupt-stop-ar",
        "signal_type": "stop",
        "language_scope": "ar",
        "phrase_variants": ("\u0642\u0641", "\u062a\u0648\u0642\u0641"),
    },
    {
        "vocabulary_id": "interrupt-cancel-ar",
        "signal_type": "cancel",
        "language_scope": "ar",
        "phrase_variants": ("\u0625\u0644\u063a\u0627\u0621", "\u0627\u0644\u063a\u0627\u0621"),
    },
)

_ARABIC_CHAR_MAP = str.maketrans(
    {
        "\u0623": "\u0627",
        "\u0625": "\u0627",
        "\u0622": "\u0627",
        "\u0671": "\u0627",
        "\u0629": "\u0647",
        "\u0649": "\u064a",
        "\u0624": "\u0648",
        "\u0626": "\u064a",
        "\u0640": "",
    }
)
_NON_WORD_RE = re.compile(r"[^\w\s\u0600-\u06FF]")
_WHITESPACE_RE = re.compile(r"\s+")
_ARABIC_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")

_ENGLISH_NOISE_TOKENS = frozenset(
    {
        "please",
        "plz",
        "ok",
        "okay",
        "assistant",
        "the",
        "to",
        "me",
        "just",
        "now",
    }
)
_ARABIC_NOISE_TOKENS = frozenset(
    {
        "\u0645\u0646",  # من
        "\u0641\u0636\u0644\u0643",  # فضلك
        "\u0644\u0648",  # لو
        "\u0633\u0645\u062d\u062a",  # سمحت
        "\u0627\u0631\u062c\u0648\u0643",  # ارجوك
        "\u0631\u062c\u0627\u0621",  # رجاء
        "\u064a\u0627",  # يا
        "\u0628\u0633",  # بس
        "\u062d\u0627\u0644\u064a\u0627",  # حاليا
    }
)
_NOISE_TOKENS = _ENGLISH_NOISE_TOKENS | _ARABIC_NOISE_TOKENS

_GREETING_TOKENS = frozenset(
    {
        "hi",
        "hello",
        "hey",
        "hai",
        "\u0647\u0627\u064a",  # هاي
        "\u0645\u0631\u062d\u0628\u0627",  # مرحبا
        "\u0627\u0647\u0644\u0627",  # اهلا
        "\u0647\u0644\u0627",  # هلا
    }
)

_WAKE_SINGLE_TOKEN_REWRITES = {
    "agency": "egb",
    "agancy": "egb",
    "agincy": "egb",
    "ajency": "egb",
    "egency": "egb",
    "ecb": "egb",
}

_WAKE_SEQUENCE_REWRITES: dict[tuple[str, ...], tuple[str, ...]] = {
    ("yi", "the", "p"): ("e", "g", "b"),
    ("yi", "d", "p"): ("e", "g", "b"),
    ("yi", "p"): ("e", "g", "b"),
    ("e", "g", "p"): ("e", "g", "b"),
}

_DEFAULT_WAKE_ALIASES: tuple[str, ...] = (
    "hi egb",
    "high egb",
    "egb",
    "e g b",
    "hello e g b",
    "hi e g b",
    "high e g b",
    "hi eh g b",
    "egp",
    "e g p",
    "hgb",
    "h g b",
    "agb",
    "a g b",
    "\u0645\u0631\u062d\u0628\u0627",  # مرحبا
    "\u0627\u064a \u062c\u064a \u0628\u064a",  # اي جي بي
    "\u0647\u0627\u064a \u0627\u064a \u062c\u064a \u0628\u064a",  # هاي اي جي بي
    "\u0647\u0644\u0627 \u0627\u064a \u062c\u064a \u0628\u064a",  # هلا اي جي بي
    "\u0627\u0647\u0644\u0627 \u0627\u064a \u062c\u064a \u0628\u064a",  # اهلا اي جي بي
    "\u0627\u064a\u062c\u064a",  # ايجي
    "\u0647\u0627\u064a \u0627\u064a\u062c\u064a",  # هاي ايجي
    "\u0647\u0644\u0627 \u0627\u064a\u062c\u064a",  # هلا ايجي
    "\u0627\u0647\u0644\u0627 \u0627\u064a\u062c\u064a",  # اهلا ايجي
    "\u0627\u064a\u0686\u064a \u0628\u064a",  # ايچي بي
    "\u0627\u064a \u062c\u064a\u0628\u064a",  # اي جيبي
    "\u0627\u0647\u0644\u0627 \u0627\u064a \u062c\u064a\u0628\u064a",  # اهلا اي جيبي
    "\u0627\u064a \u062c\u064a \u0628\u064a\u0647",  # اي جي بيه
    "\u0627\u0647\u0644\u0627 \u0627\u064a \u062c\u064a \u0628\u064a\u0647",  # اهلا اي جي بيه
    "\u0627\u0647\u0644\u0627 egb",  # اهلا egb
)

_PROFILE_CONFIGS: dict[WakeDetectionProfile, WakeProfileConfig] = {
    WakeDetectionProfile.STRICT: WakeProfileConfig(
        decision_threshold=0.58,
        exact_weight=0.30,
        prefix_weight=0.15,
        token_overlap_weight=0.20,
        subsequence_weight=0.10,
        compact_weight=0.10,
        greeting_weight=0.03,
        bigram_weight=0.08,
        fuzzy_weight=0.04,
        missing_greeting_penalty=0.22,
        fuzzy_gate_min=0.62,
    ),
    WakeDetectionProfile.BALANCED: WakeProfileConfig(
        decision_threshold=0.46,
        exact_weight=0.28,
        prefix_weight=0.14,
        token_overlap_weight=0.20,
        subsequence_weight=0.10,
        compact_weight=0.10,
        greeting_weight=0.05,
        bigram_weight=0.08,
        fuzzy_weight=0.05,
        missing_greeting_penalty=0.16,
        fuzzy_gate_min=0.54,
    ),
    WakeDetectionProfile.DEVELOPMENT: WakeProfileConfig(
        decision_threshold=0.40,
        exact_weight=0.24,
        prefix_weight=0.14,
        token_overlap_weight=0.18,
        subsequence_weight=0.10,
        compact_weight=0.12,
        greeting_weight=0.07,
        bigram_weight=0.08,
        fuzzy_weight=0.07,
        missing_greeting_penalty=0.08,
        fuzzy_gate_min=0.48,
    ),
}


def _resolve_profile(profile: WakeDetectionProfile | str | None) -> WakeDetectionProfile:
    if isinstance(profile, WakeDetectionProfile):
        return profile
    candidate = str(profile or WakeDetectionProfile.BALANCED.value).strip().lower()
    if candidate == WakeDetectionProfile.STRICT.value:
        return WakeDetectionProfile.STRICT
    if candidate == WakeDetectionProfile.DEVELOPMENT.value:
        return WakeDetectionProfile.DEVELOPMENT
    return WakeDetectionProfile.BALANCED


@lru_cache(maxsize=2048)
def _normalize_base(text: str) -> str:
    if not text:
        return ""
    normalized = str(text).casefold().strip()
    normalized = normalized.translate(_ARABIC_CHAR_MAP)
    normalized = _ARABIC_DIACRITICS_RE.sub("", normalized)
    normalized = _NON_WORD_RE.sub(" ", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized


def _strip_noise_tokens(tokens: tuple[str, ...]) -> tuple[str, ...]:
    if not tokens:
        return ()
    return tuple(token for token in tokens if token not in _NOISE_TOKENS)


@lru_cache(maxsize=2048)
def _normalize_with_noise_control(text: str, strip_noise_words: bool) -> str:
    normalized = _normalize_base(text)
    if not normalized:
        return normalized
    tokens = tuple(token for token in normalized.split() if token)
    tokens = _rewrite_wake_tokens(tokens)
    if not strip_noise_words:
        return " ".join(tokens).strip()
    if not tokens:
        return normalized
    tokens = _strip_noise_tokens(tokens)
    return " ".join(tokens).strip()


def normalize_text(text: str) -> str:
    """Normalize wake text for scoring and matching."""
    return _normalize_with_noise_control(str(text or ""), True)


def _normalize(text: str) -> str:
    return _normalize_with_noise_control(str(text or ""), False)


def normalize_wake_phrase(text: str) -> str:
    return _normalize(text)


def _compact(text: str) -> str:
    return normalize_wake_phrase(text).replace(" ", "")


@lru_cache(maxsize=2048)
def _compact_bigrams(compact_text: str) -> frozenset[str]:
    if len(compact_text) < 2:
        return frozenset()
    return frozenset(compact_text[index : index + 2] for index in range(len(compact_text) - 1))


def _token_overlap(left: frozenset[str], right: frozenset[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / max(1, len(right))


def _subsequence_match(candidate_tokens: tuple[str, ...], target_tokens: tuple[str, ...]) -> float:
    if not candidate_tokens or not target_tokens:
        return 0.0
    cursor = 0
    for token in candidate_tokens:
        if token == target_tokens[cursor]:
            cursor += 1
            if cursor == len(target_tokens):
                return 1.0
    return cursor / len(target_tokens)


def _bigrams_overlap(left: frozenset[str], right: frozenset[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _rewrite_wake_tokens(tokens: tuple[str, ...]) -> tuple[str, ...]:
    if len(tokens) < 2:
        return tokens
    if tokens[0] not in _GREETING_TOKENS:
        return tokens

    tail = tuple(token for token in tokens[1:] if token)
    compact_tail = tuple(token for token in tail if token not in _NOISE_TOKENS)
    if not compact_tail or len(compact_tail) > 4:
        return tokens

    if len(compact_tail) == 1:
        rewritten_single = _WAKE_SINGLE_TOKEN_REWRITES.get(compact_tail[0])
        if rewritten_single:
            return (tokens[0], rewritten_single)

    rewritten_sequence = _WAKE_SEQUENCE_REWRITES.get(compact_tail)
    if rewritten_sequence is not None:
        return (tokens[0], *rewritten_sequence)
    return tokens


def _cheap_similarity_gate(candidate_compact: str, alias_compact: str, min_score: float) -> bool:
    if not candidate_compact or not alias_compact:
        return False
    length_delta = abs(len(candidate_compact) - len(alias_compact))
    if length_delta > 3:
        return False
    shared = len(set(candidate_compact) & set(alias_compact))
    unique_len = max(1, len(set(alias_compact)))
    return (shared / unique_len) >= min_score


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _build_alias_spec(
    alias: str,
    *,
    thresholds: Mapping[str, float] | None = None,
) -> WakeAliasSpec | None:
    normalized = normalize_wake_phrase(alias)
    if not normalized:
        return None
    tokens = tuple(token for token in normalized.split() if token)
    token_set = frozenset(tokens)
    compact = normalized.replace(" ", "")
    contains_greeting = any(token in _GREETING_TOKENS for token in token_set)
    requires_greeting = (len(token_set) <= 2 and not contains_greeting and compact.isascii())
    return WakeAliasSpec(
        raw_phrase=str(alias),
        normalized_phrase=normalized,
        compact_phrase=compact,
        tokens=tokens,
        token_set=token_set,
        bigrams=_compact_bigrams(compact),
        requires_greeting=requires_greeting,
        thresholds=dict(thresholds or {}),
    )


def _default_alias_threshold(alias: WakeAliasSpec, profile: WakeDetectionProfile) -> float:
    override_value = None
    if alias.thresholds:
        override_value = alias.thresholds.get(profile.value)
    if override_value is not None:
        return max(0.0, min(1.0, float(override_value)))
    if alias.normalized_phrase in _CANONICAL_WAKE_SET:
        return {
            WakeDetectionProfile.STRICT: 0.56,
            WakeDetectionProfile.BALANCED: 0.46,
            WakeDetectionProfile.DEVELOPMENT: 0.38,
        }[profile]
    compact_len = len(alias.compact_phrase)
    if compact_len <= 3:
        return {
            WakeDetectionProfile.STRICT: 0.56,
            WakeDetectionProfile.BALANCED: 0.47,
            WakeDetectionProfile.DEVELOPMENT: 0.40,
        }[profile]
    if compact_len <= 5:
        return {
            WakeDetectionProfile.STRICT: 0.58,
            WakeDetectionProfile.BALANCED: 0.47,
            WakeDetectionProfile.DEVELOPMENT: 0.40,
        }[profile]
    return {
        WakeDetectionProfile.STRICT: 0.60,
        WakeDetectionProfile.BALANCED: 0.50,
        WakeDetectionProfile.DEVELOPMENT: 0.42,
    }[profile]


@lru_cache(maxsize=4096)
def _tokenize_cached(normalized_text: str) -> tuple[str, ...]:
    if not normalized_text:
        return ()
    return tuple(token for token in normalized_text.split() if token)


@dataclass(frozen=True)
class _WakeInputFeatures:
    normalized_phrase: str
    denoised_phrase: str
    compact_phrase: str
    tokens: tuple[str, ...]
    token_set: frozenset[str]
    bigrams: frozenset[str]
    has_greeting: bool


@lru_cache(maxsize=4096)
def _input_features(text: str) -> _WakeInputFeatures:
    normalized = normalize_wake_phrase(text)
    denoised = normalize_text(text)
    tokens = _tokenize_cached(denoised or normalized)
    token_set = frozenset(tokens)
    compact = (denoised or normalized).replace(" ", "")
    return _WakeInputFeatures(
        normalized_phrase=normalized,
        denoised_phrase=denoised,
        compact_phrase=compact,
        tokens=tokens,
        token_set=token_set,
        bigrams=_compact_bigrams(compact),
        has_greeting=any(token in _GREETING_TOKENS for token in token_set),
    )


def score_wake_phrase(
    input_phrase: str,
    alias: WakeAliasSpec | str,
    profile: WakeDetectionProfile | str = WakeDetectionProfile.BALANCED,
) -> WakeScore:
    """Score one wake alias against a recognized phrase using weighted metrics."""
    alias_spec = alias if isinstance(alias, WakeAliasSpec) else _build_alias_spec(str(alias))
    if alias_spec is None:
        return WakeScore(
            alias=str(alias),
            total_score=0.0,
            decision_threshold=1.0,
            accepted=False,
            component_scores={},
            greeting_gate_passed=False,
        )

    resolved_profile = _resolve_profile(profile)
    config = _PROFILE_CONFIGS[resolved_profile]
    features = _input_features(input_phrase)

    if not features.normalized_phrase:
        return WakeScore(
            alias=alias_spec.raw_phrase,
            total_score=0.0,
            decision_threshold=max(config.decision_threshold, _default_alias_threshold(alias_spec, resolved_profile)),
            accepted=False,
            component_scores={},
            greeting_gate_passed=False,
        )

    exact_match = 1.0 if (
        features.normalized_phrase == alias_spec.normalized_phrase
        or features.denoised_phrase == alias_spec.normalized_phrase
    ) else 0.0
    compact_exact = 1.0 if features.compact_phrase == alias_spec.compact_phrase else 0.0
    exact_score = max(exact_match, compact_exact)

    prefix_match = 1.0 if features.compact_phrase.startswith(alias_spec.compact_phrase) else 0.0
    if prefix_match == 0.0 and alias_spec.compact_phrase.startswith(features.compact_phrase):
        coverage = len(features.compact_phrase) / max(1, len(alias_spec.compact_phrase))
        if coverage >= 0.78:
            prefix_match = coverage

    compact_contains = 1.0 if alias_spec.compact_phrase in features.compact_phrase else 0.0
    if compact_contains == 0.0 and features.compact_phrase in alias_spec.compact_phrase:
        coverage = len(features.compact_phrase) / max(1, len(alias_spec.compact_phrase))
        if coverage >= 0.78:
            compact_contains = coverage
    token_overlap = _token_overlap(features.token_set, alias_spec.token_set)
    subsequence = _subsequence_match(features.tokens, alias_spec.tokens)
    bigram_overlap = _bigrams_overlap(features.bigrams, alias_spec.bigrams)
    greeting_score = 1.0 if features.has_greeting else 0.0

    fuzzy_score = 0.0
    cheap_floor = max(0.3, min(0.9, config.fuzzy_gate_min))
    if _cheap_similarity_gate(features.compact_phrase, alias_spec.compact_phrase, cheap_floor):
        fuzzy_score = _similarity(features.compact_phrase, alias_spec.compact_phrase)

    weighted_sum = (
        exact_score * config.exact_weight
        + prefix_match * config.prefix_weight
        + token_overlap * config.token_overlap_weight
        + subsequence * config.subsequence_weight
        + compact_contains * config.compact_weight
        + greeting_score * config.greeting_weight
        + bigram_overlap * config.bigram_weight
        + fuzzy_score * config.fuzzy_weight
    )
    weight_total = (
        config.exact_weight
        + config.prefix_weight
        + config.token_overlap_weight
        + config.subsequence_weight
        + config.compact_weight
        + config.greeting_weight
        + config.bigram_weight
        + config.fuzzy_weight
    )
    total_score = weighted_sum / max(1e-9, weight_total)

    allow_without_greeting = compact_exact == 1.0 and len(alias_spec.tokens) <= 1
    greeting_gate_passed = (not alias_spec.requires_greeting) or features.has_greeting or allow_without_greeting
    if alias_spec.requires_greeting and not greeting_gate_passed:
        total_score = max(0.0, total_score - config.missing_greeting_penalty)

    decision_threshold = max(config.decision_threshold, _default_alias_threshold(alias_spec, resolved_profile))
    accepted = greeting_gate_passed and total_score >= decision_threshold

    component_scores = {
        "exact_match": exact_match,
        "compact_exact": compact_exact,
        "prefix_match": prefix_match,
        "compact_contains": compact_contains,
        "token_overlap": token_overlap,
        "subsequence": subsequence,
        "bigram_overlap": bigram_overlap,
        "greeting": greeting_score,
        "fuzzy": fuzzy_score,
    }
    return WakeScore(
        alias=alias_spec.raw_phrase,
        total_score=total_score,
        decision_threshold=decision_threshold,
        accepted=accepted,
        component_scores=component_scores,
        greeting_gate_passed=greeting_gate_passed,
    )


def detect_wake(
    input_phrase: str,
    profile: WakeDetectionProfile | str = WakeDetectionProfile.BALANCED,
    aliases: Iterable[WakeAliasSpec | str] | None = None,
) -> WakeDetectionDecision:
    """Detect wake phrase using profile-aware weighted scoring."""
    resolved_profile = _resolve_profile(profile)
    normalized_input = normalize_wake_phrase(input_phrase)
    if not normalized_input:
        return WakeDetectionDecision(
            accepted=False,
            normalized_phrase="",
            profile=resolved_profile.value,
            matched_alias=None,
            best_score=0.0,
            decision_threshold=_PROFILE_CONFIGS[resolved_profile].decision_threshold,
            component_scores={},
            greeting_gate_passed=False,
        )

    if normalized_input in _CANONICAL_WAKE_SET:
        return WakeDetectionDecision(
            accepted=True,
            normalized_phrase=normalized_input,
            profile=resolved_profile.value,
            matched_alias=normalized_input,
            best_score=1.0,
            decision_threshold=0.0,
            component_scores={"exact_match": 1.0},
            greeting_gate_passed=True,
        )

    candidate_aliases = aliases if aliases is not None else _DEFAULT_WAKE_ALIAS_SPECS
    best_score: WakeScore | None = None
    for alias in candidate_aliases:
        score = score_wake_phrase(normalized_input, alias, resolved_profile)
        if best_score is None or score.total_score > best_score.total_score:
            best_score = score

    if best_score is None:
        return WakeDetectionDecision(
            accepted=False,
            normalized_phrase=normalized_input,
            profile=resolved_profile.value,
            matched_alias=None,
            best_score=0.0,
            decision_threshold=_PROFILE_CONFIGS[resolved_profile].decision_threshold,
            component_scores={},
            greeting_gate_passed=False,
        )

    return WakeDetectionDecision(
        accepted=best_score.accepted,
        normalized_phrase=normalized_input,
        profile=resolved_profile.value,
        matched_alias=best_score.alias,
        best_score=best_score.total_score,
        decision_threshold=best_score.decision_threshold,
        component_scores=dict(best_score.component_scores),
        greeting_gate_passed=best_score.greeting_gate_passed,
    )


_CANONICAL_WAKE_SET: frozenset[str] = frozenset(normalize_wake_phrase(item) for item in CANONICAL_WAKE_PHRASES)
_DEFAULT_WAKE_ALIAS_SPECS: tuple[WakeAliasSpec, ...] = tuple(
    item for item in (_build_alias_spec(alias) for alias in _DEFAULT_WAKE_ALIASES) if item is not None
)


def is_canonical_wake_phrase(text: str) -> bool:
    return normalize_wake_phrase(text) in _CANONICAL_WAKE_SET


def _build_interrupt_variant_index() -> dict[str, tuple[tuple[str, str], ...]]:
    index: dict[str, list[tuple[str, str]]] = {}
    for entry in INTERRUPT_VOCABULARY:
        vocabulary_id = str(entry["vocabulary_id"])
        signal_type = str(entry["signal_type"])
        for raw_variant in entry.get("phrase_variants", ()):
            variant = normalize_wake_phrase(str(raw_variant))
            if not variant:
                continue
            index.setdefault(variant, []).append((signal_type, vocabulary_id))
    return {key: tuple(value) for key, value in index.items()}


_INTERRUPT_VARIANT_INDEX = _build_interrupt_variant_index()


def detect_interrupt_signal(text: str) -> InterruptMatch | None:
    normalized = normalize_wake_phrase(text)
    if not normalized:
        return None

    matches = _INTERRUPT_VARIANT_INDEX.get(normalized)
    if matches:
        signal_type, vocabulary_id = matches[0]
        return InterruptMatch(
            signal_type=signal_type,
            normalized_phrase=normalized,
            matched_vocabulary_ids=(vocabulary_id,),
        )
    return None


class WakeWordDetector:
    """Profile-aware wake detector over recognized text (not raw audio KWS)."""

    def __init__(
        self,
        wake_names: Iterable[str] | None = None,
        start_phrases: Iterable[str] | None = None,
        stop_phrases: Iterable[str] | None = None,
        *,
        profile: WakeDetectionProfile | str = WakeDetectionProfile.BALANCED,
        telemetry_hook: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        configured_wake_names = tuple(wake_names or _DEFAULT_WAKE_ALIASES)
        self.profile = _resolve_profile(profile)
        self.wake_names = [normalize_wake_phrase(item) for item in configured_wake_names]
        self.start_phrases = [normalize_wake_phrase(item) for item in (start_phrases or ())]
        self.stop_phrases = [normalize_wake_phrase(item) for item in (stop_phrases or ())]
        self._alias_specs: tuple[WakeAliasSpec, ...] = tuple(
            item for item in (_build_alias_spec(alias) for alias in configured_wake_names) if item is not None
        )
        self._telemetry_hook = telemetry_hook
        self._telemetry_state = {
            "attempts": 0,
            "accepts": 0,
            "rejects": 0,
            "false_accepts": 0,
            "false_rejects": 0,
            "last_score": 0.0,
            "last_profile": self.profile.value,
            "last_alias": None,
        }

    def set_profile(self, profile: WakeDetectionProfile | str) -> None:
        self.profile = _resolve_profile(profile)
        self._telemetry_state["last_profile"] = self.profile.value

    def set_telemetry_hook(self, hook: Callable[[dict[str, Any]], None] | None) -> None:
        self._telemetry_hook = hook

    def telemetry_snapshot(self) -> WakeTelemetrySnapshot:
        attempts = int(self._telemetry_state["attempts"])
        accepts = int(self._telemetry_state["accepts"])
        rejects = int(self._telemetry_state["rejects"])
        false_accepts = int(self._telemetry_state["false_accepts"])
        false_rejects = int(self._telemetry_state["false_rejects"])
        return WakeTelemetrySnapshot(
            attempts=attempts,
            accepts=accepts,
            rejects=rejects,
            false_accepts=false_accepts,
            false_rejects=false_rejects,
            false_accept_rate=(false_accepts / accepts) if accepts > 0 else 0.0,
            false_reject_rate=(false_rejects / rejects) if rejects > 0 else 0.0,
            last_score=float(self._telemetry_state["last_score"]),
            last_profile=str(self._telemetry_state["last_profile"]),
            last_alias=(
                str(self._telemetry_state["last_alias"])
                if self._telemetry_state["last_alias"] is not None
                else None
            ),
        )

    def detect(self, text: str) -> WakeResult | None:
        decision = detect_wake(text, profile=self.profile, aliases=self._alias_specs)
        normalized = decision.normalized_phrase
        if not normalized:
            return None

        self._record_detection_attempt(decision)
        if decision.accepted:
            return WakeResult(action=WakeAction.START, phrase=normalized)
        return None

    def report_detection_feedback(self, *, expected_wake: bool, detected: bool) -> WakeTelemetrySnapshot:
        if detected and not expected_wake:
            self._telemetry_state["false_accepts"] = int(self._telemetry_state["false_accepts"]) + 1
        if expected_wake and not detected:
            self._telemetry_state["false_rejects"] = int(self._telemetry_state["false_rejects"]) + 1

        snapshot = self.telemetry_snapshot()
        self._emit_telemetry(
            {
                "event": "wake_feedback",
                "expected_wake": bool(expected_wake),
                "detected": bool(detected),
                "snapshot": snapshot.__dict__,
            }
        )
        return snapshot

    def _record_detection_attempt(self, decision: WakeDetectionDecision) -> None:
        self._telemetry_state["attempts"] = int(self._telemetry_state["attempts"]) + 1
        if decision.accepted:
            self._telemetry_state["accepts"] = int(self._telemetry_state["accepts"]) + 1
        else:
            self._telemetry_state["rejects"] = int(self._telemetry_state["rejects"]) + 1

        self._telemetry_state["last_score"] = float(decision.best_score)
        self._telemetry_state["last_profile"] = str(decision.profile)
        self._telemetry_state["last_alias"] = decision.matched_alias

        snapshot = self.telemetry_snapshot()
        self._emit_telemetry(
            {
                "event": "wake_detection",
                "accepted": decision.accepted,
                "normalized_phrase": decision.normalized_phrase,
                "matched_alias": decision.matched_alias,
                "score": decision.best_score,
                "decision_threshold": decision.decision_threshold,
                "component_scores": dict(decision.component_scores),
                "greeting_gate_passed": decision.greeting_gate_passed,
                "snapshot": snapshot.__dict__,
            }
        )

    def _matches_fuzzy_wake_name(self, tokens: list[str]) -> bool:
        candidate = " ".join(token for token in tokens if token)
        decision = detect_wake(candidate, profile=self.profile, aliases=self._alias_specs)
        return decision.accepted

    def _emit_telemetry(self, payload: dict[str, Any]) -> None:
        if self._telemetry_hook is None:
            return
        try:
            self._telemetry_hook(payload)
        except Exception:  # noqa: BLE001
            return


class LocalKeywordWakeDetector:
    """Local keyword wake detector using on-device speech recognition."""

    def __init__(self, *, poll_timeout_s: float = 0.8, phrase_limit_s: float = 1.6) -> None:
        self._poll_timeout_s = max(0.2, float(poll_timeout_s))
        self._phrase_limit_s = max(0.5, float(phrase_limit_s))
        self._recognizer = sr.Recognizer() if sr is not None else None
        self._stop_requested = threading.Event()
        self._active_source_lock = threading.Lock()
        self._active_source = None
        self._keywords: tuple[tuple[str, float], ...] = (
            ("hi egb", 1e-20),
            ("marhaba", 1e-20),
        )

    def clear_stop_request(self) -> None:
        self._stop_requested.clear()

    def _stop_active_source(self) -> None:
        with self._active_source_lock:
            source = self._active_source
        if source is None:
            return
        stream = getattr(source, "stream", None)
        if stream is None:
            return
        stop_stream = getattr(stream, "stop_stream", None)
        if callable(stop_stream):
            try:
                stop_stream()
            except Exception:  # noqa: BLE001
                return

    def request_stop(self) -> None:
        self._stop_requested.set()
        self._stop_active_source()

    def is_available(self) -> bool:
        if sr is None or self._recognizer is None:
            return False
        recognize_sphinx = getattr(self._recognizer, "recognize_sphinx", None)
        return callable(recognize_sphinx)

    def wait_for_wake(
        self,
        *,
        timeout_s: float = 1.0,
        interrupt_event: threading.Event | None = None,
    ) -> WakeResult | None:
        if not self.is_available():
            return None
        self.clear_stop_request()
        timeout_value = max(0.2, float(timeout_s))
        deadline = time.monotonic() + timeout_value
        checker = getattr(interrupt_event, "is_set", None) if interrupt_event is not None else None
        while time.monotonic() < deadline:
            if self._stop_requested.is_set() or (callable(checker) and checker()):
                return None
            window_timeout = min(self._poll_timeout_s, max(0.1, deadline - time.monotonic()))
            phrase_limit = min(self._phrase_limit_s, max(0.3, deadline - time.monotonic()))
            try:
                with sr.Microphone() as source:
                    with self._active_source_lock:
                        self._active_source = source
                    if self._stop_requested.is_set() or (callable(checker) and checker()):
                        return None
                    audio = self._recognizer.listen(
                        source,
                        timeout=window_timeout,
                        phrase_time_limit=phrase_limit,
                    )
                with self._active_source_lock:
                    self._active_source = None
                if self._stop_requested.is_set() or (callable(checker) and checker()):
                    return None
                text = self._recognizer.recognize_sphinx(
                    audio,
                    keyword_entries=list(self._keywords),
                )
            except Exception:  # noqa: BLE001
                with self._active_source_lock:
                    self._active_source = None
                if self._stop_requested.is_set() or (callable(checker) and checker()):
                    return None
                # Avoid tight spin when the microphone/driver fails.
                time.sleep(0.03)
                continue
            normalized = normalize_wake_phrase(str(text or ""))
            if not normalized:
                continue

            if normalized == "\u0645\u0631\u062d\u0628\u0627" or "marhaba" in normalized:
                return WakeResult(action=WakeAction.START, phrase="\u0645\u0631\u062d\u0628\u0627")

            decision = detect_wake(
                normalized,
                profile=WakeDetectionProfile.STRICT,
                aliases=("hi egb", "e g b", "egb"),
            )
            if decision.accepted:
                return WakeResult(action=WakeAction.START, phrase="hi egb")
        return None
