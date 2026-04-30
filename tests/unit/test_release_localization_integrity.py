"""Unit tests for critical localization integrity checks."""

from __future__ import annotations

from core.critical_prompts import surface_binding_payloads
from core.release_localization import (
    validate_critical_prompts,
    validate_parser_keyword_integrity,
    validate_surface_bindings,
)


def test_validate_critical_prompts_detects_mojibake_missing_and_language_mismatch() -> None:
    catalog = {
        "startup_ready": {"ar": "المساعد جاهز.", "en": "Assistant ready."},
        "offline_guidance": {"ar": "ط§ظ„ظ†طµ ط§ظ„طھط§ظ„ظپ", "en": "Network unavailable. Try again when connected."},
        "confirmation_required": {"ar": "Please confirm this protected command.", "en": ""},
    }

    results = validate_critical_prompts(catalog)
    by_key_lang = {(item.prompt_key, item.language): item for item in results}

    assert by_key_lang[("startup_ready", "ar")].status == "passed"
    assert by_key_lang[("offline_guidance", "ar")].failure_reason == "mojibake_pattern"
    assert by_key_lang[("confirmation_required", "ar")].failure_reason == "language_mismatch"
    assert by_key_lang[("confirmation_required", "en")].failure_reason == "missing"


def test_validate_surface_bindings_detects_embedded_text_and_unapproved_surface() -> None:
    bindings = surface_binding_payloads()
    broken_bindings = [dict(binding) for binding in bindings]
    broken_bindings[0]["prompt_key"] = "embedded_startup_text"
    broken_bindings.append(
        {
            "surface_id": "runtime.offline.custom_warning",
            "module_path": "core.assistant_runtime",
            "flow": "offline",
            "prompt_key": "offline_guidance",
            "resolution_method": "catalog_lookup",
        }
    )

    results = validate_surface_bindings(broken_bindings)
    by_surface = {item.surface_id: item for item in results if item.status == "failed"}

    assert by_surface["runtime.startup.ready"].failure_reason == "embedded_text"
    assert by_surface["runtime.offline.custom_warning"].failure_reason == "unapproved_surface"


def test_validate_parser_keyword_integrity_detects_unexpected_unicode() -> None:
    results = validate_parser_keyword_integrity(
        {
            "enable_obstacle_detection": (
                "start obstacle detection",
                "تشغيل العوائق",
                "تشغيل العوائق\u0007",
            ),
        }
    )
    failed = [item for item in results if item.status == "failed"]
    assert failed
    assert failed[0].failure_reason == "unexpected_unicode"
