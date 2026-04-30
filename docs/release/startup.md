# Release Startup Guide

## Purpose

Define the repeatable startup path for pilot validation and release signoff
with interpreter-pinned execution and review-ready artifact evidence.

## Standard Startup Steps

1. Activate the project virtual environment and install pinned dependencies.
2. Verify audio input/output and runtime permissions.
3. Run release validation through the active interpreter:
   `python scripts/release_validate.py --candidate-id <candidate> --commit-sha <sha>`.
4. Confirm the run summary records:
   `execution_context`, `executed_checks`, `failed_blocking_gates`,
   `expected_artifact_kinds`, and `artifact_manifest_id`.
5. Confirm every run enumerates the base artifact categories:
   `gate_summary`, `test_results`, and `diagnostic_artifact_index`.
6. Check run-specific categories (`checklist_evidence`,
   `baseline_comparison`, `localization_results`, `override_record`) and
   verify any missing entries are explicitly listed.
7. Proceed to checklist completion and signoff.

## Reproducibility Drill

1. Re-run the same validation inputs 20 times from the same active
   interpreter, repository state, and working directory.
2. Compare pass/fail decision and expected artifact kinds across all runs.

Acceptance:
- At least 19 of 20 runs keep the same final decision and expected artifact
  categories.

## Phase 21 STT Rollout Validation Sequence

Run the focused Phase 21 validation sequence with the active interpreter:

```powershell
python -m pytest tests/unit/test_stt_observability_contract.py tests/unit/test_stt_rollout_modes.py tests/unit/test_stt_failure_scenario_contract.py tests/unit/test_pocketsphinx_decommission_contract.py -q
python -m pytest tests/integration/test_stt_observability_pipeline.py tests/integration/test_stt_rollout_release_gates.py tests/integration/test_stt_failure_scenario_recovery.py tests/integration/test_pi_qualification_release_gates.py tests/integration/test_pocketsphinx_decommission.py -q
python -m pytest tests/smoke/test_stt_rollout_observability_quickstart.py -q
python -m compileall core tests scripts
python -m ruff check .
```

Evidence expected in release artifacts for STT rollout review:

- `stt-events.json`
- `stt-rollup.json`
- `stt-failure-scenarios.json`
- `stt-release-gate.json`
- `pi4-stt-qualification.json` (when qualification evidence is supplied)
- `pocketsphinx-decommission.json` (when decommission evidence is supplied)

## Phase 15 Evidence Snapshot (April 23, 2026)

- US1 wake-reliability validation command passed (`52 passed`).
- US2 recovery and runtime validation command passed (`80 passed`).
- US3 telemetry and release-gate validation command passed (`44 passed`).
- Full Phase 15 automated sweep passed:
  - Unit subset (`73 passed`)
  - Integration subset (`38 passed`)
  - Smoke subset (`27 passed`)
  - `python -m compileall core tests` succeeded
  - `python -m ruff check .` reported `All checks passed!`
- Raspberry Pi 4 physical qualification run is still required for pilot approval signoff.

## Troubleshooting Drill Hand-Off

1. Prepare 5 completed run bundles representing successful, failed, and
   degraded outcomes.
2. Hand them to a reviewer who did not create the runs.
3. Time each review from opening `summary.json` to naming the first relevant
   artifact and likely failure class.

Acceptance:
- All 5 reviews finish this first classification step within 5 minutes.
