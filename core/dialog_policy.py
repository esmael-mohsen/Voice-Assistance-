"""Shared dialog interpretation helpers for confirmation and clarification flows."""

from __future__ import annotations

import re
from dataclasses import dataclass

DialogOutcome = str

OUTCOME_AFFIRMATIVE: DialogOutcome = "affirmative"
OUTCOME_NEGATIVE: DialogOutcome = "negative"
OUTCOME_CANCEL: DialogOutcome = "cancel"
OUTCOME_AMBIGUOUS: DialogOutcome = "ambiguous"
OUTCOME_UNMATCHED: DialogOutcome = "unmatched"

_OUTCOME_PRECEDENCE: tuple[DialogOutcome, ...] = (
    OUTCOME_CANCEL,
    OUTCOME_NEGATIVE,
    OUTCOME_AFFIRMATIVE,
)

_PHRASE_FAMILIES: dict[DialogOutcome, tuple[str, ...]] = {
    OUTCOME_AFFIRMATIVE: (
        "yes",
        "yeah",
        "yep",
        "yes please",
        "ok",
        "okay",
        "ok please",
        "confirm",
        "confirmed",
        "absolutely",
        "ya",
        "\u0646\u0639\u0645",
        "\u0627\u064a\u0648\u0647",
        "\u0623\u064a\u0648\u0647",
        "\u0627\u064a\u0648\u0627",
        "\u0623\u064a\u0648\u0627",
        "\u062a\u0645\u0627\u0645",
        "\u0627\u0643\u064a\u062f",
        "\u0623\u0643\u064a\u062f",
    ),
    OUTCOME_NEGATIVE: (
        "no",
        "nope",
        "not now",
        "do not",
        "dont",
        "don't",
        "\u0644\u0627",
        "\u0644\u0623",
    ),
    OUTCOME_CANCEL: (
        "cancel",
        "cancel it",
        "stop",
        "abort",
        "\u0627\u0644\u063a\u0627\u0621",
        "\u0625\u0644\u063a\u0627\u0621",
        "\u0627\u0644\u063a\u064a",
        "\u0627\u0644\u063a\u064a\u0647",
    ),
}


@dataclass(frozen=True)
class DialogInterpretationResult:
    raw_utterance: str
    normalized_utterance: str
    matched_outcomes: tuple[DialogOutcome, ...]
    final_outcome: DialogOutcome
    safe_precedence_applied: bool


def normalize_dialog_text(text: str | None) -> str:
    normalized = str(text or "").strip().lower()
    if not normalized:
        return ""
    normalized = normalized.replace("'", " ")
    normalized = re.sub(r"[^\w\s]+", " ", normalized, flags=re.UNICODE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _contains_phrase(normalized_text: str, phrase: str) -> bool:
    candidate = normalize_dialog_text(phrase)
    if not normalized_text or not candidate:
        return False
    padded_text = f" {normalized_text} "
    padded_phrase = f" {candidate} "
    return padded_phrase in padded_text


def _match_outcomes(normalized_text: str) -> tuple[DialogOutcome, ...]:
    matches: list[DialogOutcome] = []
    for outcome in _OUTCOME_PRECEDENCE:
        phrases = _PHRASE_FAMILIES.get(outcome, ())
        if any(_contains_phrase(normalized_text, phrase) for phrase in phrases):
            matches.append(outcome)
    return tuple(matches)


def interpret_yes_no_cancel(text: str | None) -> DialogInterpretationResult:
    normalized = normalize_dialog_text(text)
    matched_outcomes = _match_outcomes(normalized)
    if not matched_outcomes:
        return DialogInterpretationResult(
            raw_utterance=str(text or ""),
            normalized_utterance=normalized,
            matched_outcomes=matched_outcomes,
            final_outcome=OUTCOME_UNMATCHED,
            safe_precedence_applied=False,
        )

    final_outcome = matched_outcomes[0]
    safe_precedence_applied = False
    if len(matched_outcomes) > 1:
        safe_precedence_applied = final_outcome in {OUTCOME_CANCEL, OUTCOME_NEGATIVE}
        if final_outcome not in {OUTCOME_CANCEL, OUTCOME_NEGATIVE, OUTCOME_AFFIRMATIVE}:
            final_outcome = OUTCOME_AMBIGUOUS

    return DialogInterpretationResult(
        raw_utterance=str(text or ""),
        normalized_utterance=normalized,
        matched_outcomes=matched_outcomes,
        final_outcome=final_outcome,
        safe_precedence_applied=safe_precedence_applied,
    )


def is_affirmative(text: str | None) -> bool:
    return interpret_yes_no_cancel(text).final_outcome == OUTCOME_AFFIRMATIVE


def stt_recovery_prompt(
    *,
    failure_category: str,
    bounded_outcome: str,
    language: str = "en-US",
) -> str:
    lang = str(language or "en-US").strip().lower()
    is_arabic = lang.startswith("ar")
    key = (str(failure_category or "").strip().lower(), str(bounded_outcome or "").strip().lower())
    prompts_en: dict[tuple[str, str], str] = {
        ("network", "retry"): "Network issue. I will retry now.",
        ("network", "fallback"): "Network issue. Switching to local fallback.",
        ("credentials", "safe_refusal"): "Cloud credentials are unavailable. Command cancelled safely.",
        ("quota_or_rate", "standby"): "Cloud limit reached. Returning to standby.",
        ("cloud_timeout", "fallback"): "Cloud timed out. Switching to local fallback.",
        ("fallback_missing", "safe_refusal"): "Local fallback is unavailable. Command cancelled safely.",
        ("language_mismatch", "retry"): "Language mismatch detected. Please repeat.",
        ("clipping", "retry"): "I heard clipped audio. Please repeat clearly.",
    }
    prompts_ar: dict[tuple[str, str], str] = {
        ("network", "retry"): "في مشكلة شبكة. سأعيد المحاولة الآن.",
        ("network", "fallback"): "في مشكلة شبكة. سأنتقل للمسار المحلي.",
        ("credentials", "safe_refusal"): "بيانات اعتماد السحابة غير متاحة. تم الإلغاء بأمان.",
        ("quota_or_rate", "standby"): "تم الوصول لحد الخدمة. سأعود لوضع الاستعداد.",
        ("cloud_timeout", "fallback"): "مهلة السحابة انتهت. سأنتقل للمسار المحلي.",
        ("fallback_missing", "safe_refusal"): "المسار المحلي غير متاح. تم الإلغاء بأمان.",
        ("language_mismatch", "retry"): "تم اكتشاف اختلاف لغة. من فضلك أعد المحاولة.",
        ("clipping", "retry"): "الصوت غير مكتمل. من فضلك أعد الكلام بوضوح.",
    }
    default_en = "I could not complete that safely. Returning to standby."
    default_ar = "لم أستطع إكمال الطلب بأمان. سأعود لوضع الاستعداد."
    if is_arabic:
        return prompts_ar.get(key, default_ar)
    return prompts_en.get(key, default_en)
