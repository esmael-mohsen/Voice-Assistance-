# Release Gate Result Contract

## Purpose

Define the readiness payload used to block or approve STT rollout for pilot and
field validation.

## Blocking Gate Shape

```json
{
  "gate_id": "stt-rollout-gate-001",
  "gate_name": "strict_fallback_available",
  "gate_status": "failed",
  "blocking_level": "pilot_and_field",
  "reason_code": "strict_fallback_missing",
  "evidence_refs": ["artifacts/run-001/stt/rollup.json"],
  "cloud_configuration_status": "passed",
  "strict_fallback_status": "failed",
  "wake_fallback_status": "passed",
  "protected_command_status": "passed",
  "bilingual_regression_status": "passed",
  "bounded_recovery_status": "passed",
  "pi4_qualification_status": "passed",
  "pocketsphinx_default_usage_count": 0,
  "field_safe_payload": true
}
```

## Rules

- Failed safety-critical gates block pilot and field approval.
- Missing cloud configuration, missing strict fallback, unsafe wake fallback,
  protected-command regression, bilingual regression, bounded-recovery
  regression, default PocketSphinx usage, and missing or failed Pi 4
  qualification are blocking.
- `pocketsphinx_default_usage_count` must be zero for production readiness.
- Evidence references must point to field-safe local release artifacts.

## Validation Expectations

- Unit tests cover pass/fail/blocking combinations.
- Integration tests prove release validation blocks unsafe rollout evidence
  and approves only when all required gate evidence passes.
