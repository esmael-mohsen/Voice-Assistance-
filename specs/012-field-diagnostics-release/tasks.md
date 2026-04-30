# Tasks: Field Diagnostics and Release Consistency

**Input**: Design documents from `/specs/012-field-diagnostics-release/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are REQUIRED because this feature changes release
validation execution, runtime orchestration diagnostics, artifact evidence, and
field-facing troubleshooting guidance.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this belongs to (e.g. `US1`, `US2`, `US3`)
- Include exact file paths in descriptions

## Path Conventions

- **Current project layout**: `main.py`, `controllers/`, `core/`, `settings/`, `tts/`, `ui/`, `tests/`, `docs/`, `scripts/`
- **Feature focus**: release execution and artifact persistence in `core/release_gates.py`, `core/release_models.py`, `core/release_artifacts.py`, and `scripts/release_validate.py`; canonical runtime diagnostics in `core/assistant_runtime.py` and `core/speech/provider_resolver.py`; operator workflow docs in `docs/release/troubleshooting.md`, `docs/release/startup.md`, and `docs/release/retention.md`
- **Specification docs**: `specs/012-field-diagnostics-release/contracts/` and `specs/012-field-diagnostics-release/quickstart.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare Phase 12 test scaffolding, smoke entry points, and validation evidence placeholders.

- [X] T001 Add Phase 12 release-validation fixtures, artifact manifest helpers, and runtime observer test doubles in `tests/conftest.py`
- [X] T002 [P] Create release reproducibility scaffolding in `tests/unit/test_release_quality_gate_blocking.py`, `tests/unit/test_release_gate_models.py`, `tests/integration/test_release_gate_pipeline.py`, and `tests/integration/test_release_workflow.py`
- [X] T003 [P] Create canonical runtime-diagnostic scaffolding in `tests/unit/test_provider_selection.py`, `tests/unit/test_offline_allowlist_policy.py`, `tests/unit/test_runtime_interrupt_preemption.py`, `tests/integration/test_provider_failure_paths.py`, `tests/integration/test_runtime_offline_policy_matrix.py`, `tests/integration/test_runtime_interruptions.py`, and `tests/integration/test_gui_runtime_bridge.py`
- [X] T004 [P] Add Phase 12 smoke scaffolding and validation evidence placeholders in `tests/smoke/test_release_quality_gates_quickstart.py`, `tests/smoke/test_offline_truth_quickstart.py`, `tests/smoke/test_interrupt_safety_quickstart.py`, and `specs/012-field-diagnostics-release/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared release-result, artifact-reference, and diagnostic-envelope boundaries required by all user stories.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Add failing unit coverage for release execution context, expected or missing artifact kinds, and canonical diagnostic-event validation in `tests/unit/test_release_quality_gate_blocking.py`, `tests/unit/test_release_gate_models.py`, `tests/unit/test_provider_selection.py`, `tests/unit/test_offline_allowlist_policy.py`, and `tests/unit/test_runtime_interrupt_preemption.py`
- [X] T006 [P] Add failing integration coverage for failed-run artifact completeness and deterministic rerun behavior in `tests/integration/test_release_gate_pipeline.py` and `tests/integration/test_release_workflow.py`
- [X] T007 [P] Add failing integration coverage for canonical provider, offline-policy, and interrupt diagnostics across headless and GUI paths in `tests/integration/test_provider_failure_paths.py`, `tests/integration/test_runtime_offline_policy_matrix.py`, `tests/integration/test_runtime_interruptions.py`, and `tests/integration/test_gui_runtime_bridge.py`
- [X] T008 [P] Add failing smoke coverage for interpreter-pinned release validation and troubleshooting workflow expectations in `tests/smoke/test_release_quality_gates_quickstart.py`, `tests/smoke/test_offline_truth_quickstart.py`, and `tests/smoke/test_interrupt_safety_quickstart.py`
- [X] T009 Define `ReleaseValidationContext`, `DiagnosticArtifactReference`, and `ReleaseValidationOutcome` models in `core/release_models.py`
- [X] T010 Add canonical field-safe runtime diagnostic envelope helpers in `core/runtime_diagnostics.py`
- [X] T011 Extend artifact persistence helpers for base expected kinds (`gate_summary`, `test_results`, `diagnostic_artifact_index`), missing kinds, and linked diagnostic references in `core/release_artifacts.py`
- [X] T012 Add active-interpreter gate command resolution and invocation-context plumbing in `core/release_gates.py` and `scripts/release_validate.py`
- [X] T013 Add shared runtime diagnostic emission hooks for provider selection, offline policy, and interrupt flows in `core/assistant_runtime.py` and `core/speech/provider_resolver.py`

**Checkpoint**: Shared release-result and runtime-diagnostic boundaries are ready; user story work can begin.

---

## Phase 3: User Story 1 - Run Reproducible Release Validation (Priority: P1) MVP

**Goal**: Ensure release validation always runs through the active project interpreter and produces a reviewable result with complete summary-level artifact evidence.

**Independent Test**: Start release validation from the active project environment on comparable setups, confirm the same interpreter context is recorded, and verify failed or successful runs still expose the same reviewable artifact categories.

### Tests for User Story 1

> **NOTE: Write these tests FIRST and ensure they fail before implementation
> because this story changes constitution-protected release validation and
> artifact evidence behavior.**

- [X] T014 [P] [US1] Extend unit coverage for active-interpreter command execution and stable run-context serialization in `tests/unit/test_release_quality_gate_blocking.py` and `tests/unit/test_release_gate_models.py`
- [X] T015 [P] [US1] Add integration coverage for comparable reruns, failed-run summaries, and artifact-gap reporting in `tests/integration/test_release_gate_pipeline.py` and `tests/integration/test_release_workflow.py`
- [X] T016 [P] [US1] Add smoke coverage for active-environment release validation in `tests/smoke/test_release_quality_gates_quickstart.py`

### Implementation for User Story 1

- [X] T017 [US1] Replace PATH-dependent release-gate invocations with active-interpreter execution in `core/release_gates.py`
- [X] T018 [US1] Persist release execution context, executed checks, and final decision details in `core/release_models.py` and `scripts/release_validate.py`
- [X] T019 [US1] Surface base expected artifact kinds (`gate_summary`, `test_results`, `diagnostic_artifact_index`), conditional artifact kinds, produced artifact references, and missing kinds in `core/release_artifacts.py`, `core/release_models.py`, and `scripts/release_validate.py`
- [X] T020 [US1] Update release startup guidance for interpreter-pinned validation and artifact review in `docs/release/startup.md` and `specs/012-field-diagnostics-release/quickstart.md`
- [X] T021 [US1] Run US1 validation with the 20-rerun reproducibility protocol (`python scripts/release_validate.py --candidate-id phase12-repro --commit-sha working-tree`, `python -m pytest tests/unit/test_release_quality_gate_blocking.py tests/unit/test_release_gate_models.py tests/integration/test_release_gate_pipeline.py tests/integration/test_release_workflow.py tests/smoke/test_release_quality_gates_quickstart.py -q`) and record SC-001 and SC-004 evidence in `specs/012-field-diagnostics-release/quickstart.md`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Review Structured Runtime Diagnostics (Priority: P2)

**Goal**: Emit one canonical, field-safe structured diagnostic shape for provider-selection, offline-policy, and interrupt outcomes across headless and GUI runtime paths.

**Independent Test**: Exercise provider fallback, offline refusal, and interrupt flows in one runtime session and verify that each emitted record shares the same canonical metadata, excludes raw user utterances by default, and remains comparable across headless and GUI entry paths.

### Tests for User Story 2

- [X] T022 [P] [US2] Extend unit coverage for provider-selection and degraded-state diagnostic envelopes in `tests/unit/test_provider_selection.py` and `tests/unit/test_provider_resolver.py`
- [X] T023 [P] [US2] Extend unit coverage for offline-policy diagnostic envelopes and privacy defaults in `tests/unit/test_offline_allowlist_policy.py` and `tests/unit/test_runtime_contract.py`
- [X] T024 [P] [US2] Extend unit coverage for interrupt outcome and preemption-latency diagnostics in `tests/unit/test_runtime_interrupt_preemption.py` and `tests/unit/test_tts_engine_interruptions.py`
- [X] T025 [P] [US2] Add integration coverage for canonical provider, offline-policy, and interrupt diagnostics across headless and GUI paths in `tests/integration/test_provider_failure_paths.py`, `tests/integration/test_runtime_offline_policy_matrix.py`, `tests/integration/test_runtime_interruptions.py`, and `tests/integration/test_gui_runtime_bridge.py`
- [X] T026 [P] [US2] Add smoke coverage for field-safe diagnostic review paths in `tests/smoke/test_offline_truth_quickstart.py` and `tests/smoke/test_interrupt_safety_quickstart.py`

### Implementation for User Story 2

- [X] T027 [US2] Emit canonical provider-selection and degraded-state diagnostics in `core/assistant_runtime.py` and `core/runtime_diagnostics.py`
- [X] T028 [US2] Emit canonical offline-policy diagnostics with decision, reason code, provider context, and next state in `core/assistant_runtime.py` and `core/speech/provider_resolver.py`
- [X] T029 [US2] Emit canonical interrupt outcome diagnostics with preemption latency in `core/assistant_runtime.py`, `core/release_metrics.py`, and `core/runtime_diagnostics.py`
- [X] T030 [US2] Strip raw user utterances from default field-facing diagnostic payloads and linked release artifacts in `core/runtime_diagnostics.py`, `core/assistant_runtime.py`, and `scripts/release_validate.py`
- [X] T031 [US2] Run US2 validation (`python -m pytest tests/unit/test_provider_selection.py tests/unit/test_provider_resolver.py tests/unit/test_offline_allowlist_policy.py tests/unit/test_runtime_contract.py tests/unit/test_runtime_interrupt_preemption.py tests/unit/test_tts_engine_interruptions.py tests/integration/test_provider_failure_paths.py tests/integration/test_runtime_offline_policy_matrix.py tests/integration/test_runtime_interruptions.py tests/integration/test_gui_runtime_bridge.py tests/smoke/test_offline_truth_quickstart.py tests/smoke/test_interrupt_safety_quickstart.py -q`) and record SC-002 and SC-005 evidence in `specs/012-field-diagnostics-release/quickstart.md`

**Checkpoint**: User Stories 1 and 2 are independently functional and testable.

---

## Phase 5: User Story 3 - Follow a Pilot Log Review Workflow (Priority: P3)

**Goal**: Give operators a short, repeatable, artifact-first troubleshooting workflow that works for successful runs, failed runs, and degraded field sessions.

**Independent Test**: Hand a completed validation run and a degraded or failed session bundle to a reviewer, then verify they can follow the documented order from run summary through supporting artifacts and identify the likely failure class without a debugger.

### Tests for User Story 3

- [X] T032 [P] [US3] Add integration coverage for workflow-ordered artifact references, review-ready missing-artifact handling, and the required base artifact kinds in `tests/integration/test_release_workflow.py` and `tests/integration/test_release_gate_pipeline.py`
- [X] T033 [P] [US3] Add smoke coverage for the timed 5-bundle pilot troubleshooting review path in `tests/smoke/test_release_quality_gates_quickstart.py`, `tests/smoke/test_offline_truth_quickstart.py`, and `tests/smoke/test_interrupt_safety_quickstart.py`

### Implementation for User Story 3

- [X] T034 [US3] Rewrite the artifact-first pilot review flow around run summary, provider or degraded diagnostics, offline-policy events, interrupt outcomes, and linked supporting artifacts in `docs/release/troubleshooting.md`
- [X] T035 [US3] Align release artifact naming, manifest links, and workflow cues with the troubleshooting contract in `core/release_artifacts.py`, `scripts/release_validate.py`, and `docs/release/retention.md`
- [X] T036 [US3] Add operator guidance for successful, failed, and degraded review scenarios plus the timed 5-bundle review drill in `docs/release/startup.md` and `specs/012-field-diagnostics-release/quickstart.md`
- [X] T037 [US3] Run US3 validation with the timed 5-bundle review drill (`python -m pytest tests/integration/test_release_workflow.py tests/integration/test_release_gate_pipeline.py tests/smoke/test_release_quality_gates_quickstart.py tests/smoke/test_offline_truth_quickstart.py tests/smoke/test_interrupt_safety_quickstart.py -q`) and record SC-003 evidence in `specs/012-field-diagnostics-release/quickstart.md`

**Checkpoint**: All user stories are independently functional and testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup, contract alignment, edge-case hardening, and full validation across all stories.

- [X] T038 [P] Refresh Phase 12 contracts to match the shipped release-result, runtime-diagnostic, and troubleshooting-workflow fields in `specs/012-field-diagnostics-release/contracts/release-validation-result-contract.md`, `specs/012-field-diagnostics-release/contracts/runtime-diagnostic-event-contract.md`, and `specs/012-field-diagnostics-release/contracts/pilot-troubleshooting-workflow-contract.md`
- [X] T039 Remove stale free-form release-summary and diagnostic-shape assumptions in `core/release_gates.py`, `scripts/release_validate.py`, `core/assistant_runtime.py`, and `docs/release/troubleshooting.md`
- [X] T040 [P] Add regression coverage for missing artifacts, repeated offline-policy and interrupt events, degraded provider sessions, and GUI/headless meaning drift in `tests/unit/test_release_gate_models.py`, `tests/unit/test_runtime_interrupt_preemption.py`, `tests/integration/test_provider_failure_paths.py`, `tests/integration/test_runtime_offline_policy_matrix.py`, `tests/integration/test_runtime_interruptions.py`, and `tests/integration/test_gui_runtime_bridge.py`
- [X] T041 Run full validation sweep (`python scripts/release_validate.py --candidate-id phase12-full --commit-sha working-tree`, `python -m pytest tests/unit/test_release_quality_gate_blocking.py tests/unit/test_release_gate_models.py tests/unit/test_release_override_governance.py tests/unit/test_provider_selection.py tests/unit/test_provider_resolver.py tests/unit/test_offline_allowlist_policy.py tests/unit/test_runtime_contract.py tests/unit/test_runtime_interrupt_preemption.py tests/unit/test_tts_engine_interruptions.py -q`, `python -m pytest tests/integration/test_release_gate_pipeline.py tests/integration/test_release_workflow.py tests/integration/test_provider_failure_paths.py tests/integration/test_runtime_offline_policy_matrix.py tests/integration/test_runtime_interruptions.py tests/integration/test_gui_runtime_bridge.py -q`, `python -m pytest tests/smoke/test_release_quality_gates_quickstart.py tests/smoke/test_offline_truth_quickstart.py tests/smoke/test_interrupt_safety_quickstart.py -q`, `python -m compileall core tests`) and record outputs in `specs/012-field-diagnostics-release/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories
- **User Stories (Phases 3-5)**: Depend on Foundational completion
- **Polish (Phase 6)**: Depends on completion of the user stories selected for release scope

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on other stories
- **US2 (P2)**: Starts after Foundational; reuses the shared diagnostic envelope from Phase 2 but remains independently testable
- **US3 (P3)**: Starts after Foundational; its full workflow validation depends on the release-result and runtime-diagnostic evidence delivered by US1 and US2

### Within Each User Story

- Write the listed tests first and confirm they fail before implementation
- Land shared model, artifact, and diagnostic-envelope updates before story-specific smoke validation
- Run the listed validation command and record evidence in `specs/012-field-diagnostics-release/quickstart.md` before marking the story complete

### Parallel Opportunities

- `T002`, `T003`, and `T004` can run in parallel after `T001`
- `T006`, `T007`, and `T008` can run in parallel after `T005`
- `T014`, `T015`, and `T016` can run in parallel for US1
- `T022`, `T023`, `T024`, `T025`, and `T026` can run in parallel for US2
- `T032` and `T033` can run in parallel for US3
- `T038` and `T040` can run in parallel during Polish

---

## Parallel Example: User Story 1

```bash
Task: "Extend unit coverage for active-interpreter command execution and stable run-context serialization in tests/unit/test_release_quality_gate_blocking.py and tests/unit/test_release_gate_models.py"
Task: "Add integration coverage for comparable reruns, failed-run summaries, and artifact-gap reporting in tests/integration/test_release_gate_pipeline.py and tests/integration/test_release_workflow.py"
Task: "Add smoke coverage for active-environment release validation in tests/smoke/test_release_quality_gates_quickstart.py"
```

## Parallel Example: User Story 2

```bash
Task: "Extend unit coverage for provider-selection and degraded-state diagnostic envelopes in tests/unit/test_provider_selection.py and tests/unit/test_provider_resolver.py"
Task: "Extend unit coverage for offline-policy diagnostic envelopes and privacy defaults in tests/unit/test_offline_allowlist_policy.py and tests/unit/test_runtime_contract.py"
Task: "Extend unit coverage for interrupt outcome and preemption-latency diagnostics in tests/unit/test_runtime_interrupt_preemption.py and tests/unit/test_tts_engine_interruptions.py"
Task: "Add integration coverage for canonical provider, offline-policy, and interrupt diagnostics across headless and GUI paths in tests/integration/test_provider_failure_paths.py, tests/integration/test_runtime_offline_policy_matrix.py, tests/integration/test_runtime_interruptions.py, and tests/integration/test_gui_runtime_bridge.py"
Task: "Add smoke coverage for field-safe diagnostic review paths in tests/smoke/test_offline_truth_quickstart.py and tests/smoke/test_interrupt_safety_quickstart.py"
```

## Parallel Example: User Story 3

```bash
Task: "Add integration coverage for workflow-ordered artifact references and review-ready missing-artifact handling in tests/integration/test_release_workflow.py and tests/integration/test_release_gate_pipeline.py"
Task: "Add smoke coverage for the pilot troubleshooting review path in tests/smoke/test_release_quality_gates_quickstart.py, tests/smoke/test_offline_truth_quickstart.py, and tests/smoke/test_interrupt_safety_quickstart.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate reproducible release execution and artifact completeness before widening scope

### Incremental Delivery

1. Setup + Foundational establish release-result models, expected artifact tracking, active-interpreter execution, and canonical diagnostic helpers
2. Deliver US1 for reproducible release validation and summary-level artifact evidence
3. Deliver US2 for canonical provider, offline-policy, and interrupt diagnostics
4. Deliver US3 for artifact-first pilot troubleshooting guidance and review workflow
5. Finish with Phase 6 polish and the full validation sweep

### Parallel Team Strategy

1. Team aligns on Setup and Foundational together
2. After Phase 2:
   - Developer A: US1 release execution context and artifact completeness
   - Developer B: US2 runtime diagnostic envelopes and privacy defaults
   - Developer C: US3 troubleshooting workflow docs and review-flow validation
3. Rejoin for contract refresh, regression hardening, and final validation

---

## Notes

- `[P]` tasks are parallel-safe only after their dependency prerequisites are complete
- Every user story includes explicit test tasks because this feature changes release orchestration, runtime safety diagnostics, and field-facing evidence
- Keep diagnostic meaning runtime-owned; GUI paths must consume the same canonical event shape rather than inventing a separate one
- Default field artifacts must remain metadata-first and must not include raw user utterances unless a narrower future requirement explicitly approves that path

