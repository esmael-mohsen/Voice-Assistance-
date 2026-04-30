"""Unit coverage for critical prompt catalog normalization and runtime fallback."""

from __future__ import annotations

from core.critical_prompts import (
    INTEGRITY_FALLBACK_USED,
    INTEGRITY_REPAIRED,
    build_default_critical_prompt_catalog,
    required_prompt_keys,
    surface_binding_payloads,
)


def test_settings_snapshot_seeds_required_critical_prompt_keys(isolated_settings_manager) -> None:
    snapshot = isolated_settings_manager.get_settings_snapshot()
    catalog = snapshot["critical_prompt_catalog"]

    assert set(required_prompt_keys()).issubset(catalog.keys())
    assert all(catalog[prompt_key]["ar"] and catalog[prompt_key]["en"] for prompt_key in required_prompt_keys())


def test_apply_settings_snapshot_repairs_missing_or_corrupted_seeded_entries(isolated_settings_manager) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "critical_prompt_catalog": {
                "startup_ready": {"ar": "", "en": ""},
                "offline_guidance": {"ar": "ط§ظ„ظ†طµ ط§ظ„طھط§ظ„ظپ", "en": "Network unavailable. Try again when connected."},
            }
        },
        persist=False,
    )

    repaired = isolated_settings_manager.resolve_critical_surface("runtime.startup.ready")
    snapshot = isolated_settings_manager.get_settings_snapshot()["critical_prompt_catalog"]

    assert repaired["integrity_status"] == INTEGRITY_REPAIRED
    assert snapshot["startup_ready"] == build_default_critical_prompt_catalog()["startup_ready"]
    assert snapshot["offline_guidance"] == build_default_critical_prompt_catalog()["offline_guidance"]


def test_resolve_critical_surface_uses_same_language_fallback_when_runtime_entry_is_corrupt(
    isolated_settings_manager,
) -> None:
    isolated_settings_manager.language = "ar-EG"
    isolated_settings_manager._critical_prompt_catalog["offline_guidance"]["ar"] = "ط§ظ„ظ†طµ ط§ظ„طھط§ظ„ظپ"
    isolated_settings_manager._repaired_prompt_keys = set()

    resolved = isolated_settings_manager.resolve_critical_surface("runtime.offline.safe_refusal")

    assert resolved["integrity_status"] == INTEGRITY_FALLBACK_USED
    assert resolved["fallback_used"] is True
    assert resolved["failure_reason"] == "mojibake_pattern"
    assert resolved["language"].startswith("ar")
    assert "Network unavailable" not in resolved["text"]
    assert resolved["text"] == "لا يوجد اتصال حالياً. حاول لاحقاً."


def test_resolve_critical_surface_formats_templates(isolated_settings_manager) -> None:
    isolated_settings_manager.language = "en-US"

    resolved = isolated_settings_manager.resolve_critical_surface(
        "runtime.onboarding.name_confirm",
        format_kwargs={"name": "Mina"},
    )

    assert resolved["fallback_used"] is False
    assert resolved["text"] == "Is your name Mina? Say yes or no."


def test_critical_prompt_surface_binding_inventory_is_unique_and_complete() -> None:
    bindings = surface_binding_payloads()
    surface_ids = [binding["surface_id"] for binding in bindings]
    prompt_keys = {binding["prompt_key"] for binding in bindings}

    assert len(surface_ids) == len(set(surface_ids))
    assert {
        "runtime.offline.safe_refusal",
        "resolver.confirmation.required",
        "resolver.clarification.language.required",
        "resolver.clarification.voice.required",
        "resolver.clarification.failed",
    }.issubset(surface_ids)
    assert {
        "offline_guidance",
        "confirmation_required",
        "clarification_language_required",
        "clarification_voice_required",
        "clarification_failed",
    }.issubset(prompt_keys)
