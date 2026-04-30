# Localization Validation Contract

## Purpose

Define the release-blocking validation contract for critical prompt catalog
integrity and critical surface binding coverage.

## Validation Input Contract

```json
{
  "catalog_source": "settings/user_profile.json",
  "required_languages": ["ar", "en"],
  "required_prompt_keys": [
    "startup_ready",
    "offline_guidance",
    "confirmation_required"
  ],
  "surface_bindings": [
    {
      "surface_id": "runtime.offline.safe_refusal",
      "prompt_key": "offline_guidance"
    }
  ]
}
```

### Rules

- `catalog_source` must point to the approved runtime baseline.
- Every required prompt key must exist for both `ar` and `en`.
- Every critical surface binding must reference an approved prompt key.
- Validation must inspect both catalog entries and approved surface bindings in
  one run.

## Prompt Integrity Finding Contract

```json
{
  "scope": "catalog_entry",
  "prompt_key": "offline_guidance",
  "surface_id": null,
  "language": "ar",
  "status": "failed",
  "failure_reason": "mojibake_pattern",
  "observed_text": "[observed text]",
  "expected_source": "settings/user_profile.json",
  "blocking": true
}
```

### Rules

- `scope` must be one of `catalog_entry`, `surface_binding`, or
  `runtime_fallback`.
- `failure_reason` is required when `status=failed`.
- Allowed failure reasons:
  - `missing`
  - `replacement_character`
  - `mojibake_pattern`
  - `language_mismatch`
  - `unapproved_surface`
  - `embedded_text`
- Any failed blocking finding must fail the localization gate.
- Findings must serialize enough evidence for release artifacts and operator
  triage without reopening runtime logs.

## Gate Summary Contract

```json
{
  "gate_name": "localization_validation",
  "status": "failed",
  "failed_findings": 2,
  "failure_code": "critical_prompt_integrity_failed",
  "summary": "2 critical prompt findings failed localization validation."
}
```

### Rules

- `status` must be `passed` or `failed`.
- `failure_code` is required when `status=failed`.
- The summary must be readable by release tooling and by a human reviewer.

## Required Observability Fields

Localization validation output should include these fields when available:

- `gate_name`
- `prompt_key`
- `surface_id`
- `language`
- `status`
- `failure_reason`
- `catalog_source`

## Validation Expectations

- Unit tests for failure-reason classification
- Integration tests for catalog plus surface-binding validation
- Regression tests proving mojibake and embedded-text cases block release
- Release workflow coverage proving localization failures block
  `localization_validation` with `critical_prompt_integrity_failed`
