"""Integration tests for release localization validation gate."""

from __future__ import annotations

from core.critical_prompts import build_default_critical_prompt_catalog, surface_binding_payloads
from core.release_localization import run_localization_validation


def test_localization_validation_passes_for_clean_catalog_and_surface_registry() -> None:
    gate_result, prompt_results = run_localization_validation(
        catalog=build_default_critical_prompt_catalog(),
        surface_bindings_override=surface_binding_payloads(),
    )

    assert gate_result.status == "passed"
    assert all(item.status == "passed" for item in prompt_results)


def test_localization_validation_fails_for_corrupted_catalog_and_embedded_surface_text() -> None:
    catalog = build_default_critical_prompt_catalog()
    catalog["offline_guidance"]["ar"] = "ط§ظ„ظ†طµ ط§ظ„طھط§ظ„ظپ"

    bindings = surface_binding_payloads()
    bindings[0]["resolution_method"] = "embedded_text"

    gate_result, prompt_results = run_localization_validation(
        catalog=catalog,
        surface_bindings_override=bindings,
    )

    assert gate_result.status == "failed"
    assert gate_result.failure_code == "critical_prompt_integrity_failed"
    assert any(
        item.prompt_key == "offline_guidance"
        and item.surface_id is None
        and item.failure_reason == "mojibake_pattern"
        for item in prompt_results
    )
    assert any(
        item.surface_id == "runtime.startup.ready"
        and item.failure_reason == "embedded_text"
        for item in prompt_results
    )
