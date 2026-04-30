"""Approved critical prompt catalog and surface binding registry."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from core.text_integrity import (
    arabic_integrity_failure,
    contains_arabic_mojibake as _contains_arabic_mojibake,
    contains_replacement_character as _contains_replacement_character,
    contains_unexpected_unicode,
    normalize_nfc,
)

FAILURE_MISSING = "missing"
FAILURE_REPLACEMENT_CHARACTER = "replacement_character"
FAILURE_MOJIBAKE_PATTERN = "mojibake_pattern"
FAILURE_UNEXPECTED_UNICODE = "unexpected_unicode"
FAILURE_NOT_NORMALIZED = "not_normalized"
FAILURE_LANGUAGE_MISMATCH = "language_mismatch"
FAILURE_UNAPPROVED_SURFACE = "unapproved_surface"
FAILURE_EMBEDDED_TEXT = "embedded_text"

INTEGRITY_VALID = "valid"
INTEGRITY_REPAIRED = "repaired"
INTEGRITY_FALLBACK_USED = "fallback_used"

REQUIRED_PROMPT_LANGUAGES: tuple[str, str] = ("ar", "en")
APPROVED_CATALOG_SOURCE = "settings/user_profile.json"

# Deterministic markers based on the mojibake patterns already seen in the
# current repository. These tokens are Arabic letters rendered from UTF-8 bytes
# under a mismatched encoding path, so they are stable to match.
ARABIC_MOJIBAKE_MARKERS: tuple[str, ...] = (
    "ط§",
    "ط¹",
    "طھ",
    "ط±",
    "ط¨",
    "ط®",
    "ظ„",
    "ظ…",
    "ظ†",
    "ظٹ",
    "ظˆ",
    "ظ‡",
    "ظƒ",
)


@dataclass(frozen=True)
class CriticalPromptDefinition:
    prompt_key: str
    category: str
    approved_text: dict[str, str]
    emergency_fallback: dict[str, str]
    criticality: str = "blocking"

    def __post_init__(self) -> None:
        normalized_approved: dict[str, str] = {}
        normalized_fallback: dict[str, str] = {}
        for language in REQUIRED_PROMPT_LANGUAGES:
            approved_raw = str(self.approved_text.get(language, "") or "")
            fallback_raw = str(self.emergency_fallback.get(language, "") or "")
            require_arabic = language == "ar"
            approved_failure = arabic_integrity_failure(approved_raw, require_arabic=require_arabic)
            fallback_failure = arabic_integrity_failure(fallback_raw, require_arabic=require_arabic)
            if approved_failure is not None:
                raise ValueError(
                    f"Invalid approved_text for prompt_key={self.prompt_key} language={language}: {approved_failure}"
                )
            if fallback_failure is not None:
                raise ValueError(
                    f"Invalid emergency_fallback for prompt_key={self.prompt_key} language={language}: {fallback_failure}"
                )
            approved_value = normalize_nfc(approved_raw)
            fallback_value = normalize_nfc(fallback_raw)
            normalized_approved[language] = approved_value
            normalized_fallback[language] = fallback_value
        object.__setattr__(self, "approved_text", normalized_approved)
        object.__setattr__(self, "emergency_fallback", normalized_fallback)

    def to_catalog_entry(self) -> dict[str, str]:
        return {language: str(self.approved_text.get(language, "") or "") for language in REQUIRED_PROMPT_LANGUAGES}


@dataclass(frozen=True)
class CriticalSurfaceBinding:
    surface_id: str
    module_path: str
    flow: str
    prompt_key: str
    prompt_class: str = "other"
    barge_in_mode: str = "blocked"
    resolution_method: str = "catalog_lookup"
    fallback_allowed: bool = True

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


CRITICAL_PROMPT_DEFINITIONS: tuple[CriticalPromptDefinition, ...] = (
    CriticalPromptDefinition(
        prompt_key="startup_ready",
        category="startup",
        approved_text={"ar": "المساعد جاهز.", "en": "Assistant ready."},
        emergency_fallback={"ar": "المساعد جاهز.", "en": "Assistant ready."},
    ),
    CriticalPromptDefinition(
        prompt_key="startup_provider_unavailable",
        category="startup",
        approved_text={
            "ar": "مسارات الصوت غير متاحة. أعد التشغيل يدوياً بعد التحقق من المزود.",
            "en": "Speech providers are unavailable. Manually restart after checking provider health.",
        },
        emergency_fallback={
            "ar": "الصوت غير متاح الآن. أعد التشغيل بعد التحقق من المزود.",
            "en": "Speech is unavailable right now. Restart after checking provider health.",
        },
    ),
    CriticalPromptDefinition(
        prompt_key="startup_degraded",
        category="startup",
        approved_text={
            "ar": "تم تشغيل المسار الاحتياطي للصوت لهذه الجلسة.",
            "en": "Degraded startup: temporary legacy provider is active for this session.",
        },
        emergency_fallback={
            "ar": "تم تشغيل مسار صوت احتياطي لهذه الجلسة.",
            "en": "A fallback speech path is active for this session.",
        },
    ),
    CriticalPromptDefinition(
        prompt_key="startup_wake_hint",
        category="startup",
        approved_text={"ar": "قل: أهلاً EGB لبدء المساعد.", "en": "Say: Hi EGB to start."},
        emergency_fallback={"ar": "قل: أهلاً EGB.", "en": "Say: Hi EGB."},
    ),
    CriticalPromptDefinition(
        prompt_key="onboarding_intro",
        category="onboarding",
        approved_text={
            "ar": "هذه أول مرة للتشغيل. سأطرح عليك بعض الأسئلة. إذا لم أفهمك سأطلبها مرة أخرى.",
            "en": "First time setup. I'll ask a few questions. If I miss it, I'll ask again.",
        },
        emergency_fallback={
            "ar": "سنبدأ إعداداً سريعاً بالصوت.",
            "en": "We'll start a quick voice setup.",
        },
    ),
    CriticalPromptDefinition(
        prompt_key="onboarding_language",
        category="onboarding",
        approved_text={
            "ar": "هل تفضل العربية أم الإنجليزية؟ قل: عربي أو English.",
            "en": "Do you prefer Arabic or English? Say: Arabic or English.",
        },
        emergency_fallback={
            "ar": "اختر اللغة: عربي أو English.",
            "en": "Choose a language: Arabic or English.",
        },
    ),
    CriticalPromptDefinition(
        prompt_key="onboarding_voice",
        category="onboarding",
        approved_text={"ar": "اختر نوع الصوت: ذكر أم أنثى؟", "en": "Choose voice: male or female?"},
        emergency_fallback={"ar": "اختر الصوت: ذكر أم أنثى؟", "en": "Choose a voice: male or female?"},
    ),
    CriticalPromptDefinition(
        prompt_key="onboarding_speed",
        category="onboarding",
        approved_text={
            "ar": "اختر سرعة الكلام: عادي، سريع، بطيء، أو رقم مثل 1.2.",
            "en": "Choose speech speed: normal, fast, slow, or a number like 1.2.",
        },
        emergency_fallback={
            "ar": "اختر سرعة الكلام أو قل رقماً مثل 1.2.",
            "en": "Choose a speech speed or say a number like 1.2.",
        },
    ),
    CriticalPromptDefinition(
        prompt_key="onboarding_name",
        category="onboarding",
        approved_text={"ar": "قل اسمك.", "en": "Tell me your name."},
        emergency_fallback={"ar": "اذكر اسمك.", "en": "Say your name."},
    ),
    CriticalPromptDefinition(
        prompt_key="onboarding_name_retry",
        category="onboarding",
        approved_text={
            "ar": "عذراً، لم أسمع الاسم جيداً. قل اسمك مرة أخرى.",
            "en": "Sorry, I didn't catch that. Say your name again.",
        },
        emergency_fallback={
            "ar": "لم أسمع الاسم. أعده مرة أخرى.",
            "en": "I didn't catch the name. Please say it again.",
        },
    ),
    CriticalPromptDefinition(
        prompt_key="onboarding_name_confirm",
        category="onboarding",
        approved_text={"ar": "هل اسمك {name}؟ قل نعم أو لا.", "en": "Is your name {name}? Say yes or no."},
        emergency_fallback={"ar": "هل اسمك {name}؟", "en": "Is your name {name}?"},
    ),
    CriticalPromptDefinition(
        prompt_key="onboarding_saved",
        category="onboarding",
        approved_text={"ar": "تم حفظ الإعدادات. شكراً!", "en": "Saved. Thank you!"},
        emergency_fallback={"ar": "تم الحفظ.", "en": "Saved."},
    ),
    CriticalPromptDefinition(
        prompt_key="onboarding_retry",
        category="onboarding",
        approved_text={"ar": "حسناً، لنجرب مرة أخرى.", "en": "Okay, let's try again."},
        emergency_fallback={"ar": "لنحاول مرة أخرى.", "en": "Let's try again."},
    ),
    CriticalPromptDefinition(
        prompt_key="interrupt_stop",
        category="interrupt",
        approved_text={"ar": "تم الإيقاف.", "en": "Stopped."},
        emergency_fallback={"ar": "تم الإيقاف.", "en": "Stopped."},
    ),
    CriticalPromptDefinition(
        prompt_key="interrupt_cancel",
        category="interrupt",
        approved_text={"ar": "تم الإلغاء.", "en": "Cancelled."},
        emergency_fallback={"ar": "تم الإلغاء.", "en": "Cancelled."},
    ),
    CriticalPromptDefinition(
        prompt_key="interrupt_emergency",
        category="interrupt",
        approved_text={"ar": "تم تأكيد وضع الطوارئ.", "en": "Emergency mode acknowledged."},
        emergency_fallback={"ar": "تم تفعيل الطوارئ.", "en": "Emergency mode enabled."},
    ),
    CriticalPromptDefinition(
        prompt_key="offline_guidance",
        category="offline",
        approved_text={
            "ar": "لا يوجد اتصال. حاول مرة أخرى بعد رجوع الشبكة.",
            "en": "Network unavailable. Try again when connected.",
        },
        emergency_fallback={
            "ar": "لا يوجد اتصال حالياً. حاول لاحقاً.",
            "en": "Network is unavailable right now. Try again later.",
        },
    ),
    CriticalPromptDefinition(
        prompt_key="confirmation_required",
        category="confirmation",
        approved_text={
            "ar": "من فضلك أكد تنفيذ هذا الأمر المحمي.",
            "en": "Please confirm this protected command.",
        },
        emergency_fallback={
            "ar": "أكد تنفيذ الأمر المحمي.",
            "en": "Confirm the protected command.",
        },
    ),
    CriticalPromptDefinition(
        prompt_key="confirmation_declined",
        category="confirmation",
        approved_text={"ar": "تم إلغاء الأمر المحمي.", "en": "Protected command cancelled."},
        emergency_fallback={"ar": "تم الإلغاء.", "en": "Cancelled."},
    ),
    CriticalPromptDefinition(
        prompt_key="confirmation_expired",
        category="confirmation",
        approved_text={
            "ar": "لم يتم التأكيد. تم إلغاء الأمر للحفاظ على الأمان.",
            "en": "No confirmation received. The protected command was cancelled.",
        },
        emergency_fallback={
            "ar": "لم يصل تأكيد. تم الإلغاء حفاظاً على الأمان.",
            "en": "No confirmation arrived. The command was cancelled for safety.",
        },
    ),
    CriticalPromptDefinition(
        prompt_key="clarification_language_required",
        category="clarification",
        approved_text={
            "ar": "\u0627\u0644\u0644\u063a\u0629 \u063a\u064a\u0631 \u0648\u0627\u0636\u062d\u0629. \u0642\u0644: \u0639\u0631\u0628\u064a \u0623\u0648 English.",
            "en": "Language is missing. Say: Arabic or English.",
        },
        emergency_fallback={
            "ar": "\u0642\u0644 \u0627\u0644\u0644\u063a\u0629: \u0639\u0631\u0628\u064a \u0623\u0648 English.",
            "en": "Say the language: Arabic or English.",
        },
    ),
    CriticalPromptDefinition(
        prompt_key="clarification_voice_required",
        category="clarification",
        approved_text={
            "ar": "\u0646\u0648\u0639 \u0627\u0644\u0635\u0648\u062a \u063a\u064a\u0631 \u0648\u0627\u0636\u062d. \u0642\u0644: \u0630\u0643\u0631 \u0623\u0648 \u0623\u0646\u062b\u0649.",
            "en": "Voice type is missing. Say: male or female.",
        },
        emergency_fallback={
            "ar": "\u0642\u0644 \u0646\u0648\u0639 \u0627\u0644\u0635\u0648\u062a: \u0630\u0643\u0631 \u0623\u0648 \u0623\u0646\u062b\u0649.",
            "en": "Say the voice type: male or female.",
        },
    ),
    CriticalPromptDefinition(
        prompt_key="clarification_failed",
        category="clarification",
        approved_text={
            "ar": "\u0644\u0645 \u0623\u062a\u0645\u0643\u0646 \u0645\u0646 \u062a\u062d\u062f\u064a\u062f \u0627\u0644\u062e\u064a\u0627\u0631 \u0627\u0644\u0645\u0637\u0644\u0648\u0628. \u0623\u0648\u0642\u0641 \u0627\u0644\u0623\u0645\u0631 \u0644\u0644\u0633\u0644\u0627\u0645\u0629.",
            "en": "I still cannot determine the required option, so I am stopping safely.",
        },
        emergency_fallback={
            "ar": "\u0644\u0645 \u064a\u062a\u0636\u062d \u0627\u0644\u062e\u064a\u0627\u0631. \u0623\u0648\u0642\u0641 \u0627\u0644\u0623\u0645\u0631 \u0644\u0644\u0633\u0644\u0627\u0645\u0629.",
            "en": "The option is still unclear. Stopping safely.",
        },
    ),
)

CRITICAL_SURFACE_BINDINGS: tuple[CriticalSurfaceBinding, ...] = (
    CriticalSurfaceBinding(
        surface_id="runtime.startup.ready",
        module_path="core.assistant_runtime",
        flow="startup",
        prompt_key="startup_ready",
    ),
    CriticalSurfaceBinding(
        surface_id="runtime.startup.provider_unavailable",
        module_path="core.assistant_runtime",
        flow="startup",
        prompt_key="startup_provider_unavailable",
    ),
    CriticalSurfaceBinding(
        surface_id="runtime.startup.degraded",
        module_path="core.assistant_runtime",
        flow="startup",
        prompt_key="startup_degraded",
    ),
    CriticalSurfaceBinding(
        surface_id="runtime.startup.wake_hint",
        module_path="core.assistant_runtime",
        flow="startup",
        prompt_key="startup_wake_hint",
    ),
    CriticalSurfaceBinding(
        surface_id="runtime.onboarding.intro",
        module_path="core.assistant_runtime",
        flow="onboarding",
        prompt_key="onboarding_intro",
        prompt_class="informational",
        barge_in_mode="allowed",
    ),
    CriticalSurfaceBinding(
        surface_id="runtime.onboarding.language",
        module_path="core.assistant_runtime",
        flow="onboarding",
        prompt_key="onboarding_language",
        prompt_class="onboarding_choice",
        barge_in_mode="allowed",
    ),
    CriticalSurfaceBinding(
        surface_id="runtime.onboarding.voice",
        module_path="core.assistant_runtime",
        flow="onboarding",
        prompt_key="onboarding_voice",
        prompt_class="onboarding_choice",
        barge_in_mode="allowed",
    ),
    CriticalSurfaceBinding(
        surface_id="runtime.onboarding.speed",
        module_path="core.assistant_runtime",
        flow="onboarding",
        prompt_key="onboarding_speed",
        prompt_class="low_risk_setting",
        barge_in_mode="allowed",
    ),
    CriticalSurfaceBinding(
        surface_id="runtime.onboarding.name",
        module_path="core.assistant_runtime",
        flow="onboarding",
        prompt_key="onboarding_name",
        prompt_class="name_capture",
        barge_in_mode="allowed",
    ),
    CriticalSurfaceBinding(
        surface_id="runtime.onboarding.name_retry",
        module_path="core.assistant_runtime",
        flow="onboarding",
        prompt_key="onboarding_name_retry",
        prompt_class="retry_help",
        barge_in_mode="allowed",
    ),
    CriticalSurfaceBinding(
        surface_id="runtime.onboarding.name_confirm",
        module_path="core.assistant_runtime",
        flow="onboarding",
        prompt_key="onboarding_name_confirm",
        prompt_class="name_confirmation",
        barge_in_mode="allowed",
    ),
    CriticalSurfaceBinding(
        surface_id="runtime.onboarding.saved",
        module_path="core.assistant_runtime",
        flow="onboarding",
        prompt_key="onboarding_saved",
    ),
    CriticalSurfaceBinding(
        surface_id="runtime.onboarding.retry",
        module_path="core.assistant_runtime",
        flow="onboarding",
        prompt_key="onboarding_retry",
        prompt_class="retry_help",
        barge_in_mode="allowed",
    ),
    CriticalSurfaceBinding(
        surface_id="runtime.interrupt.stop",
        module_path="core.assistant_runtime",
        flow="interrupt",
        prompt_key="interrupt_stop",
    ),
    CriticalSurfaceBinding(
        surface_id="runtime.interrupt.cancel",
        module_path="core.assistant_runtime",
        flow="interrupt",
        prompt_key="interrupt_cancel",
    ),
    CriticalSurfaceBinding(
        surface_id="runtime.interrupt.emergency",
        module_path="core.assistant_runtime",
        flow="interrupt",
        prompt_key="interrupt_emergency",
    ),
    CriticalSurfaceBinding(
        surface_id="runtime.offline.safe_refusal",
        module_path="core.assistant_runtime",
        flow="offline",
        prompt_key="offline_guidance",
    ),
    CriticalSurfaceBinding(
        surface_id="resolver.confirmation.required",
        module_path="core.resolver",
        flow="confirmation",
        prompt_key="confirmation_required",
        prompt_class="protected_confirmation",
        barge_in_mode="blocked_until_spoken_once",
    ),
    CriticalSurfaceBinding(
        surface_id="resolver.confirmation.declined",
        module_path="core.resolver",
        flow="confirmation",
        prompt_key="confirmation_declined",
        prompt_class="protected_confirmation",
        barge_in_mode="blocked_until_spoken_once",
    ),
    CriticalSurfaceBinding(
        surface_id="resolver.confirmation.expired",
        module_path="core.resolver",
        flow="confirmation",
        prompt_key="confirmation_expired",
        prompt_class="protected_confirmation",
        barge_in_mode="blocked_until_spoken_once",
    ),
    CriticalSurfaceBinding(
        surface_id="resolver.clarification.language.required",
        module_path="core.resolver",
        flow="clarification",
        prompt_key="clarification_language_required",
    ),
    CriticalSurfaceBinding(
        surface_id="resolver.clarification.voice.required",
        module_path="core.resolver",
        flow="clarification",
        prompt_key="clarification_voice_required",
    ),
    CriticalSurfaceBinding(
        surface_id="resolver.clarification.failed",
        module_path="core.resolver",
        flow="clarification",
        prompt_key="clarification_failed",
    ),
)


_DEFINITION_BY_KEY = {item.prompt_key: item for item in CRITICAL_PROMPT_DEFINITIONS}
_BINDING_BY_SURFACE = {item.surface_id: item for item in CRITICAL_SURFACE_BINDINGS}


def build_default_critical_prompt_catalog() -> dict[str, dict[str, str]]:
    return {item.prompt_key: item.to_catalog_entry() for item in CRITICAL_PROMPT_DEFINITIONS}


def approved_catalog_source() -> str:
    return APPROVED_CATALOG_SOURCE


def required_prompt_keys() -> tuple[str, ...]:
    return tuple(item.prompt_key for item in CRITICAL_PROMPT_DEFINITIONS)


def prompt_definition(prompt_key: str) -> CriticalPromptDefinition | None:
    return _DEFINITION_BY_KEY.get(str(prompt_key or "").strip())


def surface_binding(surface_id: str) -> CriticalSurfaceBinding | None:
    return _BINDING_BY_SURFACE.get(str(surface_id or "").strip())


def surface_bindings() -> tuple[CriticalSurfaceBinding, ...]:
    return CRITICAL_SURFACE_BINDINGS


def surface_binding_payloads() -> list[dict[str, Any]]:
    return [item.to_payload() for item in CRITICAL_SURFACE_BINDINGS]


def prompt_key_for_surface(surface_id: str) -> str | None:
    binding = surface_binding(surface_id)
    if binding is None:
        return None
    return binding.prompt_key


def emergency_fallback_text(prompt_key: str, language: str) -> str:
    definition = prompt_definition(prompt_key)
    if definition is None:
        return ""
    language_key = "ar" if str(language or "").startswith("ar") else "en"
    return str(definition.emergency_fallback.get(language_key, "") or "").strip()


def approved_prompt_text(prompt_key: str, language: str) -> str:
    definition = prompt_definition(prompt_key)
    if definition is None:
        return ""
    language_key = "ar" if str(language or "").startswith("ar") else "en"
    return str(definition.approved_text.get(language_key, "") or "").strip()


def contains_replacement_character(text: str) -> bool:
    return _contains_replacement_character(text)


def contains_arabic_mojibake(text: str) -> bool:
    return _contains_arabic_mojibake(text)


def has_unexpected_unicode(text: str) -> bool:
    return contains_unexpected_unicode(text)


def language_key_for_locale(locale: str) -> str:
    return "ar" if str(locale or "").startswith("ar") else "en"
