"""Critical prompt localization integrity checks for release gating."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from core.critical_prompts import (
    APPROVED_CATALOG_SOURCE,
    FAILURE_EMBEDDED_TEXT,
    FAILURE_LANGUAGE_MISMATCH,
    FAILURE_MISSING,
    FAILURE_MOJIBAKE_PATTERN,
    FAILURE_NOT_NORMALIZED,
    FAILURE_REPLACEMENT_CHARACTER,
    FAILURE_UNAPPROVED_SURFACE,
    FAILURE_UNEXPECTED_UNICODE,
    REQUIRED_PROMPT_LANGUAGES,
    contains_arabic_mojibake,
    contains_replacement_character,
    has_unexpected_unicode,
    required_prompt_keys,
    surface_bindings,
)
from core.release_models import GateExecutionResult
from core.text_integrity import has_arabic, has_latin, normalize_nfc


@dataclass(frozen=True)
class PromptValidationResult:
    scope: str
    prompt_key: str | None
    surface_id: str | None
    language: str | None
    expected_text: str
    observed_text: str
    status: str
    failure_reason: str | None = None
    catalog_source: str = APPROVED_CATALOG_SOURCE
    blocking: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _contains_arabic(text: str) -> bool:
    return has_arabic(text)


def _contains_latin(text: str) -> bool:
    return has_latin(text)


def _failure_reason_for_text(language: str, text: str) -> str | None:
    normalized = str(text or "").strip()
    if not normalized:
        return FAILURE_MISSING
    if contains_replacement_character(normalized):
        return FAILURE_REPLACEMENT_CHARACTER
    if has_unexpected_unicode(normalized):
        return FAILURE_UNEXPECTED_UNICODE
    if normalize_nfc(normalized) != normalized:
        return FAILURE_NOT_NORMALIZED
    if language == "ar" and contains_arabic_mojibake(normalized):
        return FAILURE_MOJIBAKE_PATTERN
    if language == "ar" and not _contains_arabic(normalized) and _contains_latin(normalized):
        return FAILURE_LANGUAGE_MISMATCH
    if language == "en" and _contains_arabic(normalized):
        return FAILURE_LANGUAGE_MISMATCH
    return None


def _normalize_catalog_entry(raw_entry: Any) -> dict[str, str]:
    if not isinstance(raw_entry, Mapping):
        return {language: "" for language in REQUIRED_PROMPT_LANGUAGES}
    return {
        language: str(raw_entry.get(language, "") or "").strip()
        for language in REQUIRED_PROMPT_LANGUAGES
    }


def validate_catalog_entries(
    catalog: Mapping[str, Any],
    *,
    catalog_source: str = APPROVED_CATALOG_SOURCE,
) -> list[PromptValidationResult]:
    results: list[PromptValidationResult] = []
    normalized_catalog = {
        prompt_key: _normalize_catalog_entry(catalog.get(prompt_key))
        for prompt_key in required_prompt_keys()
    }

    for prompt_key, entry in sorted(normalized_catalog.items()):
        for language in REQUIRED_PROMPT_LANGUAGES:
            observed = entry.get(language, "")
            failure_reason = _failure_reason_for_text(language, observed)
            results.append(
                PromptValidationResult(
                    scope="catalog_entry",
                    prompt_key=prompt_key,
                    surface_id=None,
                    language=language,
                    expected_text=observed,
                    observed_text=observed,
                    status="failed" if failure_reason else "passed",
                    failure_reason=failure_reason,
                    catalog_source=catalog_source,
                )
            )
    return results


def _binding_payload(binding: Any) -> dict[str, Any]:
    if hasattr(binding, "to_payload") and callable(binding.to_payload):
        return dict(binding.to_payload())
    if isinstance(binding, Mapping):
        return {str(key): value for key, value in binding.items()}
    return {}


def validate_surface_bindings(
    binding_items: list[Any] | tuple[Any, ...],
    *,
    catalog_source: str = APPROVED_CATALOG_SOURCE,
) -> list[PromptValidationResult]:
    results: list[PromptValidationResult] = []
    expected_bindings = {binding.surface_id: binding for binding in surface_bindings()}
    observed_bindings = {_binding_payload(binding).get("surface_id"): _binding_payload(binding) for binding in binding_items}

    for surface_id, expected in sorted(expected_bindings.items()):
        observed = observed_bindings.get(surface_id)
        if not observed:
            results.append(
                PromptValidationResult(
                    scope="surface_binding",
                    prompt_key=expected.prompt_key,
                    surface_id=surface_id,
                    language=None,
                    expected_text=expected.prompt_key,
                    observed_text="",
                    status="failed",
                    failure_reason=FAILURE_UNAPPROVED_SURFACE,
                    catalog_source=catalog_source,
                )
            )
            continue

        observed_prompt_key = str(observed.get("prompt_key", "") or "")
        resolution_method = str(observed.get("resolution_method", "catalog_lookup") or "catalog_lookup")
        failure_reason: str | None = None
        if resolution_method != "catalog_lookup":
            failure_reason = FAILURE_EMBEDDED_TEXT
        elif observed_prompt_key != expected.prompt_key:
            failure_reason = FAILURE_EMBEDDED_TEXT

        results.append(
            PromptValidationResult(
                scope="surface_binding",
                prompt_key=observed_prompt_key or expected.prompt_key,
                surface_id=surface_id,
                language=None,
                expected_text=expected.prompt_key,
                observed_text=observed_prompt_key,
                status="failed" if failure_reason else "passed",
                failure_reason=failure_reason,
                catalog_source=catalog_source,
            )
        )

    for surface_id, observed in sorted(observed_bindings.items()):
        if not surface_id or surface_id in expected_bindings:
            continue
        results.append(
            PromptValidationResult(
                scope="surface_binding",
                prompt_key=str(observed.get("prompt_key", "") or "") or None,
                surface_id=surface_id,
                language=None,
                expected_text="approved surface binding",
                observed_text=str(observed.get("prompt_key", "") or ""),
                status="failed",
                failure_reason=FAILURE_UNAPPROVED_SURFACE,
                catalog_source=catalog_source,
            )
        )

    return results


def validate_critical_prompts(catalog: dict[str, dict[str, str]]) -> list[PromptValidationResult]:
    return validate_catalog_entries(catalog)


def _normalize_parser_keywords(raw_keywords: Any) -> dict[str, tuple[str, ...]]:
    if not isinstance(raw_keywords, Mapping):
        return {}
    normalized: dict[str, tuple[str, ...]] = {}
    for intent_id, phrases in raw_keywords.items():
        if isinstance(phrases, (list, tuple)):
            normalized[str(intent_id)] = tuple(str(item or "") for item in phrases)
    return normalized


def validate_parser_keyword_integrity(
    parser_keywords: Mapping[str, Any] | None = None,
    *,
    catalog_source: str = APPROVED_CATALOG_SOURCE,
) -> list[PromptValidationResult]:
    from core import parser as command_parser

    source_keywords = (
        _normalize_parser_keywords(parser_keywords)
        if parser_keywords is not None
        else _normalize_parser_keywords(command_parser.COMMAND_KEYWORDS)
    )
    results: list[PromptValidationResult] = []
    for intent_id, phrases in sorted(source_keywords.items()):
        for index, phrase in enumerate(phrases):
            phrase_text = str(phrase or "")
            language = "ar" if _contains_arabic(phrase_text) else "en"
            failure_reason = _failure_reason_for_text(language, phrase_text)
            results.append(
                PromptValidationResult(
                    scope="parser_keyword",
                    prompt_key=intent_id,
                    surface_id=f"{intent_id}#{index}",
                    language=language,
                    expected_text=phrase_text,
                    observed_text=phrase_text,
                    status="failed" if failure_reason else "passed",
                    failure_reason=failure_reason,
                    catalog_source=catalog_source,
                )
            )
    return results


def catalog_from_settings_snapshot(snapshot: Mapping[str, object]) -> dict[str, dict[str, str]]:
    raw_catalog = snapshot.get("critical_prompt_catalog", {})
    if not isinstance(raw_catalog, Mapping):
        return {}
    return {
        str(prompt_key): _normalize_catalog_entry(raw_entry)
        for prompt_key, raw_entry in raw_catalog.items()
    }


def run_localization_validation(
    *,
    catalog: dict[str, dict[str, str]],
    surface_bindings_override: list[Any] | tuple[Any, ...] | None = None,
    parser_keywords_override: Mapping[str, Any] | None = None,
    catalog_source: str = APPROVED_CATALOG_SOURCE,
) -> tuple[GateExecutionResult, list[PromptValidationResult]]:
    prompt_results = validate_catalog_entries(catalog, catalog_source=catalog_source)
    binding_results = validate_surface_bindings(
        list(surface_bindings_override or surface_bindings()),
        catalog_source=catalog_source,
    )
    parser_results = validate_parser_keyword_integrity(
        parser_keywords_override,
        catalog_source=catalog_source,
    )
    all_results = [*prompt_results, *binding_results, *parser_results]
    failed = [item for item in all_results if item.status == "failed" and item.blocking]
    if not failed:
        gate_result = GateExecutionResult(
            gate_name="localization_validation",
            status="passed",
            is_blocking=True,
            duration_ms=0,
            summary="All critical prompt findings passed localization validation.",
        )
        return gate_result, all_results

    gate_result = GateExecutionResult(
        gate_name="localization_validation",
        status="failed",
        is_blocking=True,
        duration_ms=0,
        summary=f"{len(failed)} critical prompt findings failed localization validation.",
        failure_code="critical_prompt_integrity_failed",
    )
    return gate_result, all_results


def serialize_prompt_validation_results(results: list[PromptValidationResult]) -> list[dict[str, Any]]:
    return [result.to_dict() for result in results]
