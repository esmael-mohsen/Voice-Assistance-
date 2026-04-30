# Quickstart: Localization Integrity and Prompt Hardening

## Goal

Validate that every critical Arabic and English runtime prompt is sourced from
the approved catalog, remains readable, and causes the release localization
gate to fail whenever mojibake, missing text, language mismatch, or embedded
critical text returns.

## Approved Surface Matrix

| Surface ID | Expected Prompt Key |
|---|---|
| `runtime.startup.ready` | `startup_ready` |
| `runtime.startup.provider_unavailable` | `startup_provider_unavailable` |
| `runtime.startup.degraded` | `startup_degraded` |
| `runtime.startup.wake_hint` | `startup_wake_hint` |
| `runtime.onboarding.*` | `onboarding_*` |
| `runtime.interrupt.stop` | `interrupt_stop` |
| `runtime.interrupt.cancel` | `interrupt_cancel` |
| `runtime.interrupt.emergency` | `interrupt_emergency` |
| `runtime.offline.safe_refusal` | `offline_guidance` |
| `resolver.confirmation.required` | `confirmation_required` |
| `resolver.confirmation.declined` | `confirmation_declined` |
| `resolver.confirmation.expired` | `confirmation_expired` |

## Validation Paths

1. Baseline catalog normalization:
   Confirm `settings/user_profile.json` contains every required prompt key for
   startup, onboarding, interrupt, offline, and confirmation flows.
2. Runtime critical surface resolution:
   Confirm runtime and resolver paths emit `surface_id`, `prompt_key`,
   `integrity_status`, and same-language fallback metadata for critical
   surfaces.
3. Release localization validation:
   Confirm the gate blocks on missing text, replacement characters, Arabic
   mojibake patterns, language mismatch, unapproved surfaces, and embedded
   critical text.

## Recorded Evidence

### US1 Validation

- Command:
  `python -m pytest tests/unit/test_settings_critical_prompt_catalog.py tests/integration/test_runtime_prompt_localization.py tests/smoke/test_runtime_quickstart.py -q`
- Result:
  `19 passed, 2 warnings`
- SC-001:
  Arabic startup, onboarding, offline, and interrupt prompts were emitted from
  catalog-backed surfaces with readable text.
- SC-002:
  Runtime emitted `fallback_used` / `integrity_status` metadata on critical
  surfaces and preserved Arabic fallback text.
- SC-006:
  Simulated interrupt corruption triggered same-language fallback and a runtime
  integrity signal.

### US2 Validation

- Command:
  `python -m pytest tests/integration/test_runtime_prompt_localization.py tests/integration/test_command_confirmation_localization.py -q`
- Result:
  `6 passed, 2 warnings`
- SC-005:
  Protected-command confirmations and runtime critical flows resolved through
  approved `prompt_key` bindings with no embedded-text drift in covered
  surfaces.

### US3 Validation

- Command:
  `python -m pytest tests/unit/test_release_localization_integrity.py tests/integration/test_release_localization_validation.py tests/integration/test_release_workflow.py -q`
- Result:
  `10 passed, 2 warnings`
- SC-003:
  Release validation blocked on mojibake, missing text, language mismatch, and
  embedded surface bindings while reporting `prompt_key` and `surface_id`.
- SC-004:
  Release workflow regression coverage confirmed localization failures block the
  gate with `critical_prompt_integrity_failed`.

### Full Sweep

- Unit command:
  `python -m pytest tests/unit/test_settings_critical_prompt_catalog.py tests/unit/test_release_localization_integrity.py -q`
  Result: `7 passed, 2 warnings`
- Integration command:
  `python -m pytest tests/integration/test_runtime_prompt_localization.py tests/integration/test_command_confirmation_localization.py tests/integration/test_release_localization_validation.py tests/integration/test_release_workflow.py -q`
  Result: `14 passed, 2 warnings`
- Smoke command:
  `python -m pytest tests/smoke/test_runtime_quickstart.py -q`
  Result: `11 passed, 2 warnings`
- Compile check:
  `python -m compileall core settings controllers tests`
  Result: success

## Operator Notes

- Runtime integrity metadata now emits `critical_prompt_surface_id`,
  `prompt_key`, `integrity_status`, `fallback_used`, and `catalog_source`.
- When a critical prompt is missing or corrupt at runtime, the assistant speaks
  the approved same-language emergency fallback and surfaces the integrity
  signal for correction.
- Release validation uses `settings/user_profile.json` as the baseline catalog
  source and validates both catalog entries and approved surface bindings.
