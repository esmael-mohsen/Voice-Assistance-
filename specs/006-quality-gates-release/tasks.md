# Tasks: Quality Gates and Release Preparation

**Input**: Design documents from `/specs/006-quality-gates-release/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are REQUIRED because this feature adds release-blocking validation, baseline policy enforcement, override governance, and safety-critical readiness gates.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g. `US1`, `US2`, `US3`)
- Include exact file paths in descriptions

## Path Conventions

- **Current project layout**: `main.py`, `controllers/`, `core/`, `settings/`, `tts/`, `ui/`, `tests/`, `docs/`
- **Feature focus**: release validation modules in `core/`, policy/config in `settings/`, validation suites in `tests/unit/`, `tests/integration/`, `tests/smoke/`, and operator docs in `docs/`
- **Specification docs**: `specs/006-quality-gates-release/contracts/` and `specs/006-quality-gates-release/quickstart.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare deterministic scaffolding for release-gate implementation and evidence capture.

- [X] T001 Add shared release-validation fixtures and artifact temp-directory helpers in `tests/conftest.py`
- [X] T002 [P] Create unit test modules for release gate domains in `tests/unit/test_release_gate_models.py`, `tests/unit/test_release_override_governance.py`, and `tests/unit/test_release_latency_baselines.py`
- [X] T003 [P] Create integration and smoke test modules for release pipeline validation in `tests/integration/test_release_gate_pipeline.py`, `tests/integration/test_release_workflow.py`, and `tests/smoke/test_release_quality_gates_quickstart.py`
- [X] T004 [P] Create release documentation folder and placeholders in `docs/release/troubleshooting.md`, `docs/release/startup.md`, `docs/release/checklist.md`, and `docs/release/retention.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build core release-gate primitives required by all user stories.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Add failing unit coverage for release-run, gate-result, checklist, and manifest entities in `tests/unit/test_release_gate_models.py`
- [X] T006 [P] Add failing unit coverage for dual-approval overrides and 48-hour remediation windows in `tests/unit/test_release_override_governance.py`
- [X] T007 [P] Add failing integration coverage for deterministic gate order and fail-fast behavior in `tests/integration/test_release_gate_pipeline.py`
- [X] T008 Implement release domain models and enums in `core/release_models.py`
- [X] T009 [P] Implement release artifact manifest and retention utility functions in `core/release_artifacts.py`
- [X] T010 [P] Implement release gate orchestration shell (ordered execution + blocking semantics) in `core/release_gates.py`
- [X] T011 Implement emergency override governance service in `core/release_override.py`
- [X] T012 [P] Add release-threshold and retention policy configuration in `settings/release_thresholds.json` and `settings/settings_manager.py`
- [X] T013 Implement structured release-gate logging hooks in `core/dispatcher.py` and `core/assistant_runtime.py`

**Checkpoint**: Foundation ready; user story implementation can begin.

---

## Phase 3: User Story 1 - Prevent Regressions Before Pilot Builds (Priority: P1) MVP

**Goal**: Block releases when lifecycle, primary-journey, or critical localization regressions are detected.

**Independent Test**: Run lifecycle + journey + localization suites and confirm release status remains blocked until all blocking checks pass.

### Tests for User Story 1

- [X] T014 [P] [US1] Add lifecycle regression integration tests for startup/standby/wake/listening/speaking/error/offline transitions in `tests/integration/test_release_lifecycle_validation.py`
- [X] T015 [P] [US1] Add primary-journey regression integration tests for critical assistant flows in `tests/integration/test_release_journey_validation.py`
- [X] T016 [P] [US1] Add Arabic/English critical prompt integrity tests in `tests/unit/test_release_localization_integrity.py` and `tests/integration/test_release_localization_validation.py`

### Implementation for User Story 1

- [X] T017 [US1] Implement lifecycle validation runner and result serialization in `core/release_lifecycle_checks.py`
- [X] T018 [P] [US1] Implement primary-journey validation runner and gate outputs in `core/release_journey_checks.py`
- [X] T019 [US1] Implement critical prompt catalog loading and AR/EN integrity validator in `core/release_localization.py` and `settings/settings_manager.py`
- [X] T020 [US1] Integrate lifecycle/journey/localization checks into the release gate pipeline in `core/release_gates.py`
- [X] T021 [US1] Persist US1 gate evidence artifacts and update run summaries in `core/release_artifacts.py`
- [X] T022 [US1] Run US1 validation (`pytest tests/integration/test_release_lifecycle_validation.py tests/integration/test_release_journey_validation.py tests/integration/test_release_localization_validation.py`) and record SC-001/SC-003 evidence in `specs/006-quality-gates-release/quickstart.md`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Understand Readiness Through Measurable Baselines (Priority: P2)

**Goal**: Capture required latency metrics and fail release when any per-metric degradation threshold is breached.

**Independent Test**: Execute baseline capture and comparison for all required metrics and verify run failure on any threshold breach.

### Tests for User Story 2

- [X] T023 [P] [US2] Add unit tests for baseline normalization and per-metric threshold evaluation in `tests/unit/test_release_latency_baselines.py`
- [X] T024 [P] [US2] Add integration tests for metric capture and fail-on-breach gate behavior in `tests/integration/test_release_latency_pipeline.py`

### Implementation for User Story 2

- [X] T025 [US2] Implement latency metric capture hooks for `wake_to_listen`, `listen_to_result`, and `result_to_speech_start` in `core/release_metrics.py` and `core/assistant_runtime.py`
- [X] T026 [P] [US2] Implement baseline snapshot storage and approved-baseline lookup in `core/release_baselines.py`
- [X] T027 [US2] Implement per-metric degradation decision logic using policy config in `core/release_gates.py` and `settings/release_thresholds.json`
- [X] T028 [US2] Generate baseline comparison artifacts and report payloads in `core/release_artifacts.py`
- [X] T029 [US2] Run US2 validation (`pytest tests/unit/test_release_latency_baselines.py tests/integration/test_release_latency_pipeline.py`) and record SC-002/FR-005A evidence in `specs/006-quality-gates-release/quickstart.md`

**Checkpoint**: User Stories 1 and 2 are independently functional and testable.

---

## Phase 5: User Story 3 - Ship with Repeatable Release Hygiene (Priority: P3)

**Goal**: Enforce reproducible release workflow with pinned dependencies, automated gates, troubleshooting/startup guidance, checklist evidence, override auditability, and retention policy.

**Independent Test**: Execute the standard release workflow and confirm compile/test/lint gating, checklist completion, override governance, and artifact retention behavior.

### Tests for User Story 3

- [X] T030 [P] [US3] Add unit tests for compile/test/lint blocking behavior and override role enforcement in `tests/unit/test_release_quality_gate_blocking.py` and `tests/unit/test_release_override_governance.py`
- [X] T031 [P] [US3] Add integration and smoke tests for end-to-end release workflow/checklist paths in `tests/integration/test_release_workflow.py` and `tests/smoke/test_release_quality_gates_quickstart.py`

### Implementation for User Story 3

- [X] T032 [US3] Pin runtime and dev dependencies for reproducible release gating in `requirements.txt`
- [X] T033 [US3] Implement release gate CLI entrypoint for compile/test/lint/checklist execution in `scripts/release_validate.py`
- [X] T034 [P] [US3] Implement override audit persistence and remediation breach flagging in `core/release_override.py` and `core/release_artifacts.py`
- [X] T035 [P] [US3] Author operator troubleshooting and startup docs in `docs/release/troubleshooting.md` and `docs/release/startup.md`
- [X] T036 [US3] Author release checklist template and checklist validation mapping in `docs/release/checklist.md` and `core/release_gates.py`
- [X] T037 [US3] Implement 180-day artifact retention enforcement notes and helper integration in `docs/release/retention.md` and `core/release_artifacts.py`
- [X] T038 [US3] Run US3 validation (`pytest tests/unit/test_release_quality_gate_blocking.py tests/integration/test_release_workflow.py tests/smoke/test_release_quality_gates_quickstart.py`) and record SC-004/SC-005/SC-006/SC-007 evidence in `specs/006-quality-gates-release/quickstart.md`

**Checkpoint**: All user stories are independently functional and testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final alignment, hardening, and full validation across stories.

- [X] T039 [P] Update contract examples to match implemented payloads in `specs/006-quality-gates-release/contracts/release-quality-gates-contract.md` and `specs/006-quality-gates-release/contracts/override-governance-contract.md`
- [X] T040 Refine and de-duplicate release gate orchestration logic in `core/release_gates.py`, `core/release_models.py`, and `core/release_artifacts.py`
- [X] T041 [P] Add edge-case regression coverage for missing metrics, flaky reruns, and startup audio-permission drift in `tests/integration/test_release_workflow.py` and `tests/unit/test_release_quality_gate_blocking.py`
- [X] T042 Run full validation sweep (`python -m compileall main.py core settings tts ui tests`, `python -m pytest tests/unit -q`, `python -m pytest tests/integration -q`, `python -m pytest tests/smoke -q`, `ruff check .`) and capture outputs in `specs/006-quality-gates-release/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories
- **User Stories (Phases 3-5)**: Depend on Foundational completion
- **Polish (Phase 6)**: Depends on completion of user stories selected for release scope

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on other stories
- **US2 (P2)**: Starts after Foundational; independent of US1 implementation details
- **US3 (P3)**: Starts after Foundational; final end-to-end workflow validation should run after US1 and US2 gates are available

### Within Each User Story

- Write listed tests first and confirm they fail before implementation
- Implement core logic before running story-level validation commands
- Record evidence in `specs/006-quality-gates-release/quickstart.md` before marking story done

### Parallel Opportunities

- `T002`, `T003`, and `T004` can run in parallel after `T001`
- `T006`, `T007`, `T009`, `T010`, and `T012` can run in parallel after `T005` and `T008`
- `T014`, `T015`, and `T016` can run in parallel for US1
- `T023` and `T024` can run in parallel for US2
- `T030` and `T031` can run in parallel for US3
- `T034` and `T035` can run in parallel within US3
- `T039` and `T041` can run in parallel in the Polish phase

---

## Parallel Example: User Story 1

```bash
Task: "Add lifecycle regression integration tests in tests/integration/test_release_lifecycle_validation.py"
Task: "Add primary-journey regression integration tests in tests/integration/test_release_journey_validation.py"
Task: "Add Arabic/English critical prompt integrity tests in tests/unit/test_release_localization_integrity.py and tests/integration/test_release_localization_validation.py"
```

## Parallel Example: User Story 2

```bash
Task: "Add unit tests for baseline normalization and threshold evaluation in tests/unit/test_release_latency_baselines.py"
Task: "Add integration tests for metric capture and fail-on-breach behavior in tests/integration/test_release_latency_pipeline.py"
```

## Parallel Example: User Story 3

```bash
Task: "Add unit tests for compile/test/lint blocking and override role enforcement in tests/unit/test_release_quality_gate_blocking.py and tests/unit/test_release_override_governance.py"
Task: "Add integration/smoke workflow tests in tests/integration/test_release_workflow.py and tests/smoke/test_release_quality_gates_quickstart.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate lifecycle/journey/localization blocking behavior before widening scope

### Incremental Delivery

1. Setup + Foundational establish reusable release-gate infrastructure
2. Deliver US1 for regression prevention
3. Deliver US2 for measurable baseline decisioning
4. Deliver US3 for repeatable release hygiene and governance
5. Finish with Phase 6 polish and full validation sweep

### Parallel Team Strategy

1. Team aligns on Setup and Foundational together
2. After Phase 2:
   - Developer A: US1 lifecycle/journey/localization gates
   - Developer B: US2 baseline capture/compare pipeline
   - Developer C: US3 release workflow/docs/governance
3. Rejoin for cross-cutting polish and final validation

---

## Notes

- `[P]` tasks are parallel-safe only after dependency prerequisites are complete
- Every user story includes explicit test tasks because this feature is safety-critical and gate-driven
- Keep headless runtime behavior as release-readiness source of truth
- Preserve audit evidence for gates, overrides, and checklist signoff in every story phase
