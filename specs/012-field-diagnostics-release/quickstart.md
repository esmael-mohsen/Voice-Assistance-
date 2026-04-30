# Quickstart: Field Diagnostics and Release Consistency

## Goal

Validate that release runs are reproducible inside the active project
environment, that failed runs still leave usable artifact evidence, that
provider, offline-policy, and interrupt outcomes emit the same canonical
diagnostic shape, and that an operator can follow the troubleshooting workflow
without a debugger.

## Preconditions

1. Use the project virtual environment and repository root.
2. Run release validation from the same interpreter environment you intend to
   ship or validate.
3. Keep artifact output available under `artifacts/<run-id>/` after each run.
4. Exercise both headless and GUI-driven runtime paths when validating
   cross-entrypoint diagnostic consistency.

## Validation Paths

### 1. Interpreter-Pinned Release Validation

1. Start a release validation run from the active project interpreter.
2. Let the workflow execute compile, test, lint, and checklist gates.
3. Open the run summary and confirm it records the run context and executed
   checks.
4. Repeat the same validation inputs for 20 comparable reruns from the same
   interpreter, repository state, and working directory.
5. Compare the final decision and expected artifact categories across all 20
   reruns.

Expected outcome:
- The run executes through the same active interpreter context that launched
  the workflow.
- The run summary clearly identifies execution context and final decision.
- At least 19 of 20 reruns keep the same pass or fail decision and expected
  artifact categories.

### 2. Failed-Run Artifact Completeness

1. Trigger a controlled failing release-validation scenario.
2. Let the run stop with a failed status.
3. Review the run summary, per-gate results, and diagnostic artifact index.
4. Confirm the run enumerates the base artifact categories
   `gate_summary`, `test_results`, and `diagnostic_artifact_index`.
5. Confirm any missing run-specific artifact categories are explicitly
   identified rather than silently omitted.

Expected outcome:
- Failed runs still produce summary-level evidence.
- Per-gate results remain available for the executed checks.
- Artifact gaps are surfaced as reviewable metadata.

### 3. Provider and Degraded Diagnostics

1. Exercise a runtime session that selects a provider successfully.
2. Repeat with a degraded or unavailable provider scenario.
3. Inspect the emitted structured diagnostics.
4. Confirm both records expose the canonical metadata shape and degraded reason
   where applicable.

Expected outcome:
- Provider diagnostics use the same core fields in both ready and degraded
  cases.
- The active provider context and next runtime state are clear without reading
  free-form logs.

### 4. Offline-Policy Decision Diagnostics

1. Exercise one allowed offline-policy case, one downgraded case, and one
   safely refused case.
2. Inspect the emitted structured diagnostic records.
3. Confirm each record identifies the decision, reason code, user outcome, and
   next state.

Expected outcome:
- Offline-policy diagnostics explain why the runtime allowed, downgraded, or
  refused execution.
- Reviewers can classify the result from the structured record alone.

### 5. Interrupt Outcome and Latency Diagnostics

1. Exercise speech or capability interruption during active runtime work.
2. Capture the resulting diagnostic record.
3. Verify the record includes interrupt outcome, resulting state, and measured
   preemption latency when available.

Expected outcome:
- Interrupt diagnostics expose both the behavioral outcome and timing context.
- Preemption latency can be reviewed without reconstructing it from raw logs.

### 6. Troubleshooting Workflow

1. Open a completed validation run and `docs/release/troubleshooting.md`.
2. Use 5 representative completed run bundles, including successful, failed,
   and degraded sessions, and give them to a reviewer who did not create them.
3. Time each review from opening the run summary until the reviewer names the
   first relevant artifact and likely failure class.
4. Follow the prescribed review order from run summary through supporting
   artifacts for each bundle.

Expected outcome:
- The reviewer identifies the first high-signal artifact and likely failure
  class within 5 minutes for all 5 bundles.
- The workflow works for successful, failed, and degraded sessions without a
  debugger.

### 7. Headless and GUI Diagnostic Parity

1. Exercise the same provider, offline-policy, or interrupt failure class in a
   headless run.
2. Repeat the scenario from the GUI-driven debug path.
3. Compare the emitted structured diagnostic records.

Expected outcome:
- Diagnostic meaning stays consistent across both entry paths.
- GUI-specific presentation does not change the canonical event shape.

## Suggested Validation Commands

- `python scripts/release_validate.py --candidate-id phase12-repro --commit-sha working-tree`
- `python -m pytest tests/unit/test_release_quality_gate_blocking.py tests/unit/test_release_gate_models.py tests/unit/test_release_override_governance.py -q`
- `python -m pytest tests/integration/test_release_gate_pipeline.py tests/integration/test_release_workflow.py tests/integration/test_runtime_offline_policy_matrix.py tests/integration/test_runtime_interruptions.py -q`
- `python -m pytest tests/smoke/test_release_quality_gates_quickstart.py tests/smoke/test_offline_truth_quickstart.py tests/smoke/test_interrupt_safety_quickstart.py -q`
- `python -m compileall core tests`

## Operator Notes

- Field artifacts should stay metadata-first and must not rely on raw user
  utterances to explain common failure classes.
- If a run is incomplete, start from the run summary and missing artifact
  references before inspecting deeper logs.
- Base artifact categories for every run are `gate_summary`, `test_results`,
  and `diagnostic_artifact_index`; `checklist_evidence`,
  `baseline_comparison`, `localization_results`, and `override_record` remain
  conditional by run type.
- Headless evidence is the primary field-debugging path; GUI validation is a
  parity check, not a different troubleshooting model.

## Validation Evidence (2026-04-21)

- **US1 / SC-001 / SC-004 reproducibility tooling**:
  `python scripts/release_validate.py --candidate-id phase12-repro --commit-sha working-tree`
  completed with structured outcome and artifact index (`run-1776786207`), with
  expected gating failure on `checklist_validation` because
  `docs/release/checklist.md` remains intentionally unchecked for pre-signoff
  development runs.
- **US1 test suite**:
  `python -m pytest tests/unit/test_release_quality_gate_blocking.py tests/unit/test_release_gate_models.py tests/integration/test_release_gate_pipeline.py tests/integration/test_release_workflow.py tests/smoke/test_release_quality_gates_quickstart.py -q`
  passed as part of the consolidated Phase 12 sweep.
- **US2 / SC-002 / SC-005 diagnostics coverage**:
  `python -m pytest tests/unit/test_provider_selection.py tests/unit/test_provider_resolver.py tests/unit/test_offline_allowlist_policy.py tests/unit/test_runtime_contract.py tests/unit/test_runtime_interrupt_preemption.py tests/unit/test_tts_engine_interruptions.py tests/integration/test_provider_failure_paths.py tests/integration/test_runtime_offline_policy_matrix.py tests/integration/test_runtime_interruptions.py tests/integration/test_gui_runtime_bridge.py tests/smoke/test_offline_truth_quickstart.py tests/smoke/test_interrupt_safety_quickstart.py -q`
  passed.
- **US3 / SC-003 workflow coverage**:
  `python -m pytest tests/integration/test_release_workflow.py tests/integration/test_release_gate_pipeline.py tests/smoke/test_release_quality_gates_quickstart.py tests/smoke/test_offline_truth_quickstart.py tests/smoke/test_interrupt_safety_quickstart.py -q`
  passed; timed-review drill procedure documented in `docs/release/startup.md`
  and this quickstart.
- **Full Phase 12 sweep**:
  `python -m pytest tests/unit/test_release_quality_gate_blocking.py tests/unit/test_release_gate_models.py tests/unit/test_release_override_governance.py tests/unit/test_provider_selection.py tests/unit/test_provider_resolver.py tests/unit/test_offline_allowlist_policy.py tests/unit/test_runtime_contract.py tests/unit/test_runtime_interrupt_preemption.py tests/unit/test_tts_engine_interruptions.py -q` passed (`49` tests).
  `python -m pytest tests/integration/test_release_gate_pipeline.py tests/integration/test_release_workflow.py tests/integration/test_provider_failure_paths.py tests/integration/test_runtime_offline_policy_matrix.py tests/integration/test_runtime_interruptions.py tests/integration/test_gui_runtime_bridge.py -q` passed (`23` tests).
  `python -m pytest tests/smoke/test_release_quality_gates_quickstart.py tests/smoke/test_offline_truth_quickstart.py tests/smoke/test_interrupt_safety_quickstart.py -q` passed (`9` tests).
  `python -m compileall core tests` passed.
  `python scripts/release_validate.py --candidate-id phase12-full --commit-sha working-tree`
  completed with structured outcome and artifact index (`run-1776786232`), with
  the same expected `checklist_validation` gate failure pending checklist
  signoff.
