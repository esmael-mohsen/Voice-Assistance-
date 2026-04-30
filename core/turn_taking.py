"""Turn-taking policy helpers for guided voice interactions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TurnWindowStatus = Literal[
    "speaking_only",
    "speaking_with_barge_in",
    "listening",
    "closed_vocabulary_listening",
    "waiting_confirmation",
    "recovering",
]

PromptClass = Literal[
    "onboarding_choice",
    "low_risk_setting",
    "informational",
    "retry_help",
    "name_capture",
    "name_confirmation",
    "protected_confirmation",
    "shutdown",
    "destructive",
    "other",
]

DEFAULT_SAFE_PREEMPTION_VOCABULARY: tuple[str, ...] = (
    "stop",
    "cancel",
    "emergency",
    "قف",
    "توقف",
    "الغاء",
    "إلغاء",
)

_PROMPT_CLASS_BY_SURFACE: dict[str, PromptClass] = {
    "runtime.onboarding.intro": "informational",
    "runtime.onboarding.language": "onboarding_choice",
    "runtime.onboarding.voice": "onboarding_choice",
    "runtime.onboarding.speed": "low_risk_setting",
    "runtime.onboarding.name": "name_capture",
    "runtime.onboarding.name_retry": "retry_help",
    "runtime.onboarding.name_confirm": "name_confirmation",
    "runtime.onboarding.retry": "retry_help",
    "runtime.startup.ready": "informational",
    "runtime.startup.wake_hint": "informational",
    "runtime.offline.safe_refusal": "informational",
    "resolver.confirmation.required": "protected_confirmation",
    "resolver.confirmation.declined": "protected_confirmation",
    "resolver.confirmation.expired": "protected_confirmation",
}

_CLOSED_VOCABULARY_BY_SURFACE: dict[str, str] = {
    "runtime.onboarding.language": "onboarding.language_choice",
    "runtime.onboarding.voice": "onboarding.voice_choice",
    "runtime.onboarding.speed": "onboarding.speed_choice",
    "runtime.onboarding.name_confirm": "confirmation.yes_no_cancel",
    "resolver.confirmation.required": "confirmation.yes_no_cancel",
}

_EARLY_BARGE_IN_CLASSES: frozenset[PromptClass] = frozenset(
    {
        "onboarding_choice",
        "low_risk_setting",
        "informational",
        "retry_help",
        "name_capture",
        "name_confirmation",
    }
)

_PROTECTED_CLASSES: frozenset[PromptClass] = frozenset(
    {"protected_confirmation", "shutdown", "destructive"}
)


@dataclass(frozen=True)
class TurnTakingWindow:
    """Machine-readable turn-taking decision for one guided prompt window."""

    status: TurnWindowStatus
    prompt_class: PromptClass
    prompt_surface_id: str
    barge_in_allowed: bool
    global_safety_only_preemption: bool
    closed_vocabulary_id: str | None = None
    retry_count: int = 0


def prompt_class_for_surface(surface_id: str) -> PromptClass:
    key = str(surface_id or "").strip()
    return _PROMPT_CLASS_BY_SURFACE.get(key, "other")


def closed_vocabulary_for_surface(surface_id: str) -> str | None:
    key = str(surface_id or "").strip()
    return _CLOSED_VOCABULARY_BY_SURFACE.get(key)


def is_global_safety_command(utterance: str) -> bool:
    normalized = str(utterance or "").strip().lower()
    if not normalized:
        return False
    for token in DEFAULT_SAFE_PREEMPTION_VOCABULARY:
        candidate = str(token or "").strip().lower()
        if candidate and candidate in normalized:
            return True
    return False


def build_turn_window(
    *,
    prompt_surface_id: str,
    retry_count: int = 0,
    protected_prompt_spoken_once: bool = False,
) -> TurnTakingWindow:
    prompt_class = prompt_class_for_surface(prompt_surface_id)
    closed_vocabulary_id = closed_vocabulary_for_surface(prompt_surface_id)
    is_protected = prompt_class in _PROTECTED_CLASSES
    barge_in_allowed = prompt_class in _EARLY_BARGE_IN_CLASSES
    if is_protected and not protected_prompt_spoken_once:
        barge_in_allowed = False

    if is_protected:
        status: TurnWindowStatus = "speaking_only"
    elif closed_vocabulary_id:
        status = "speaking_with_barge_in" if barge_in_allowed else "speaking_only"
    else:
        status = "speaking_with_barge_in" if barge_in_allowed else "speaking_only"

    return TurnTakingWindow(
        status=status,
        prompt_class=prompt_class,
        prompt_surface_id=str(prompt_surface_id or ""),
        barge_in_allowed=barge_in_allowed,
        global_safety_only_preemption=is_protected,
        closed_vocabulary_id=closed_vocabulary_id,
        retry_count=max(0, int(retry_count)),
    )


def listening_status_for_window(window: TurnTakingWindow) -> TurnWindowStatus:
    if window.closed_vocabulary_id:
        return "closed_vocabulary_listening"
    if window.prompt_class in _PROTECTED_CLASSES:
        return "waiting_confirmation"
    return "listening"


def should_accept_preemption(
    *,
    utterance: str,
    window: TurnTakingWindow,
) -> bool:
    if not window.global_safety_only_preemption:
        return True
    return is_global_safety_command(utterance)

