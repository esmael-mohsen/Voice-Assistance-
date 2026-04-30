# Release Quality Gates Contract

## Purpose

Define the machine-readable input and output contract for release validation
gates, including blocking behavior, baseline comparisons, and localization
integrity checks.

## Gate Run Input Contract

```json
{
  "run_id": "run-2026-04-19-001",
  "candidate_id": "pilot-0.6.0-rc1",
  "commit_sha": "abc1234",
  "trigger": "ci",
  "profile": "wearable_headless",
  "gates": [
    "compile",
    "unit_tests",
    "integration_tests",
    "smoke_tests",
    "lint",
    "lifecycle_validation",
    "journey_validation",
    "localization_validation",
    "baseline_compare",
    "checklist_validation"
  ]
}
```

### Rules

- `run_id`, `candidate_id`, and `commit_sha` are required.
- `gates` must be an ordered list for deterministic execution.
- Gate names must match the approved enum values.

## Gate Stage Result Contract

```json
{
  "gate_name": "integration_tests",
  "status": "passed",
  "is_blocking": true,
  "duration_ms": 18432,
  "failure_code": null,
  "summary": "All integration suites passed.",
  "evidence_ref": "artifacts/run-2026-04-19-001/integration-tests.xml"
}
```

### Rules

- `status` must be one of `passed`, `failed`, `skipped`, `overridden`.
- `failure_code` is required for `status=failed`.
- Blocking gate failure marks run as failed unless an approved emergency
  override exists.

## Latency Baseline Comparison Contract

```json
{
  "metric_name": "wake_to_listen",
  "current_p95_ms": 840,
  "baseline_p95_ms": 760,
  "delta_ms": 80,
  "delta_pct": 10.53,
  "threshold_ms": 100,
  "threshold_pct": 12.0,
  "breached": false,
  "decision_reason": "Within approved per-metric limits"
}
```

### Rules

- Comparison is required for all three wearable metrics:
  `wake_to_listen`, `listen_to_result`, `result_to_speech_start`.
- Any metric with `breached=true` fails `baseline_compare`.
- Threshold values must come from approved policy records.

## Localization Validation Result Contract

```json
{
  "prompt_key": "startup_ready",
  "language": "ar",
  "expected_text": "المساعد جاهز",
  "observed_text": "المساعد جاهز",
  "status": "passed",
  "failure_reason": null
}
```

### Rules

- Every critical prompt key must be validated for both `ar` and `en`.
- Failed prompt entries must include `failure_reason`.
- Any failed critical prompt fails `localization_validation`.

## Gate Run Summary Contract

```json
{
  "run_id": "run-2026-04-19-001",
  "status": "failed",
  "failed_blocking_gates": ["baseline_compare"],
  "override_required": false,
  "artifact_manifest_id": "manifest-run-2026-04-19-001",
  "completed_at": "2026-04-19T14:10:00Z"
}
```

### Rules

- Final status must be one of:
  `passed`, `failed`, `override_pending`, `approved_with_override`.
- `approved_with_override` requires linked override record.
- `artifact_manifest_id` is mandatory for all completed runs.

## Required Observability Fields

Gate telemetry should include these keys when available:

- `run_id`
- `candidate_id`
- `gate_name`
- `status`
- `duration_ms`
- `failure_code`
- `metric_name`
- `breached`
- `artifact_manifest_id`

## Validation Expectations

- Unit tests for gate status transitions and blocking behavior.
- Integration tests for full pipeline ordering and failure propagation.
- Regression tests for localization and baseline breach handling.
