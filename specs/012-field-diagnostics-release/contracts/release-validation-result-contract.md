# Release Validation Result Contract

## Purpose

Define the machine-readable result emitted after a release validation run so
operators can verify execution context, executed checks, final decision, and
artifact completeness from one summary surface.

## Output Shape

```json
{
  "run_id": "run-1713705600",
  "candidate_id": "pilot-build-12",
  "commit_sha": "working-tree",
  "status": "failed",
  "execution_context": {
    "python_executable": "D:/EGB_FUNCTIONS/voice_assistant/.venv/Scripts/python.exe",
    "working_directory": "D:/EGB_FUNCTIONS/voice_assistant",
    "invoked_command": "python scripts/release_validate.py --candidate-id pilot-build-12 --commit-sha working-tree"
  },
  "executed_checks": [
    "compile",
    "unit_tests",
    "integration_tests",
    "smoke_tests",
    "lint",
    "checklist_validation"
  ],
  "failed_blocking_gates": [
    "lint"
  ],
  "expected_artifact_kinds": [
    "gate_summary",
    "test_results",
    "diagnostic_artifact_index",
    "checklist_evidence",
    "baseline_comparison"
  ],
  "artifact_references": [
    {
      "kind": "gate_summary",
      "path": "artifacts/run-1713705600/summary.json",
      "checksum": "sha256:123",
      "available": true
    },
    {
      "kind": "test_results",
      "path": "artifacts/run-1713705600/gate-results.json",
      "checksum": "sha256:456",
      "available": true
    },
    {
      "kind": "diagnostic_artifact_index",
      "path": "artifacts/run-1713705600/diagnostic-artifacts.json",
      "checksum": "sha256:789",
      "available": true
    },
    {
      "kind": "baseline_comparison",
      "path": "",
      "checksum": "",
      "available": false,
      "source": "missing",
      "notes": "No baseline comparison was produced for this failed pre-baseline run."
    }
  ],
  "missing_artifact_kinds": [
    "baseline_comparison"
  ],
  "final_decision_reason": "lint gate failed",
  "artifact_manifest_id": "manifest-run-1713705600"
}
```

## Rules

- `execution_context.python_executable` must match the interpreter used to run
  the release checks.
- `executed_checks` must contain every gate actually attempted by the run.
- Every run must enumerate `gate_summary`, `test_results`, and
  `diagnostic_artifact_index` as base expected artifact kinds.
- Every run must include run-summary and per-gate evidence even when the final
  status is `failed`.
- `checklist_evidence`, `baseline_comparison`, `localization_results`, and
  `override_record` are conditional expected kinds that appear only when the
  run produces or requires those artifacts.
- `missing_artifact_kinds` must list every expected category whose artifact
  reference is unavailable.
- Artifact gaps must be explicit in the result payload rather than inferred
  from silent omissions.

## Required Observability Fields

- `run_id`
- `status`
- `execution_context.python_executable`
- `execution_context.working_directory`
- `executed_checks`
- `failed_blocking_gates`
- `expected_artifact_kinds`
- `artifact_references`
- `missing_artifact_kinds`
- `final_decision_reason`
- `artifact_manifest_id`

## Validation Expectations

- Unit coverage for interpreter-pinned gate execution and artifact-kind
  completeness logic.
- Integration coverage for failed runs that still emit summary and per-gate
  evidence.
- Smoke validation for end-to-end release run reproducibility from the active
  project environment.
