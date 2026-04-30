# Tasks: Runtime Extraction

**Input**: Design documents from `/specs/001-runtime-extraction/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED because this feature changes runtime orchestration,
settings application, lifecycle handling, and safety-sensitive behavior.

**Organization**: Tasks are grouped by user story to enable incremental
implementation, validation, and delivery.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Current project layout**: `main.py`, `controllers/`, `core/`, `settings/`,
  `tts/`, `ui/`, `tests/`, `docs/`
- **New architecture slices**: add `core/assistant_runtime.py` only; do not add
  a new top-level package
- Always use real repository paths from `plan.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the test and validation structure needed for the runtime
extraction.

- [X] T001 Create the runtime test package structure in `tests/unit/__init__.py`, `tests/integration/__init__.py`, and `tests/smoke/__init__.py`
- [X] T002 Create shared runtime fixtures and doubles in `tests/conftest.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the shared runtime models and validation scaffolding that
all user stories depend on.

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Create the shared runtime state, event, and observer models in `core/assistant_runtime.py`
- [X] T004 Add settings snapshot and onboarding-configuration persistence helpers in `settings/settings_manager.py`
- [X] T005 [P] Add runtime unit-test scaffolding in `tests/unit/test_assistant_runtime.py`
- [X] T006 [P] Add runtime integration-test scaffolding in `tests/integration/test_runtime_modes.py`
- [X] T007 [P] Add smoke-validation scaffolding for parity and failure cases in `tests/smoke/test_runtime_quickstart.py`

**Checkpoint**: Foundation ready - shared runtime scaffolding exists, tests are
ready to drive implementation, and user story work can proceed.

---

## Phase 3: User Story 1 - Consistent Runtime Behavior (Priority: P1) MVP

**Goal**: Deliver one shared runtime loop and onboarding flow that powers both
GUI and console mode with the same user-visible behavior.

**Independent Test**: Start the assistant in GUI and console mode, wake it, run
the same supported command, and confirm the same lifecycle and onboarding flow
occur in both modes.

### Tests for User Story 1

> **NOTE: Write these tests FIRST and ensure they fail before implementation
> because this story changes constitution-protected runtime behavior**

- [X] T008 [P] [US1] Add lifecycle, protected-intent, and onboarding parity tests in `tests/unit/test_assistant_runtime.py`
- [X] T009 [P] [US1] Add GUI/console parity integration tests in `tests/integration/test_runtime_modes.py`

### Implementation for User Story 1

- [X] T010 [US1] Implement the shared runtime loop, structured lifecycle logging, protected close/stop/shutdown intent handling, failure recovery, and first-run onboarding in `core/assistant_runtime.py`
- [X] T011 [US1] Refactor console startup to use the shared runtime in `main.py`
- [X] T012 [US1] Align runtime dependency attachment and profile persistence with the shared runtime in `settings/settings_manager.py` and `settings/profile_store.py`
- [X] T013 [US1] Validate configured-user and first-run parity scenarios in `tests/smoke/test_runtime_quickstart.py`

**Checkpoint**: User Story 1 is complete when GUI and console mode both run on
the same runtime service and preserve existing behavior.

---

## Phase 4: User Story 2 - UI as Observer, Not Owner (Priority: P2)

**Goal**: Convert the debug UI path into a pure observer/bridge that no longer
owns the assistant runtime.

**Independent Test**: Run the assistant with the debug UI and confirm the UI
only mirrors shared runtime events while the runtime remains operational
without UI ownership.

### Tests for User Story 2

- [X] T014 [P] [US2] Add runtime-bridge translation tests in `tests/unit/test_assistant_worker.py`
- [X] T015 [P] [US2] Add GUI observer integration tests in `tests/integration/test_gui_runtime_bridge.py`

### Implementation for User Story 2

- [X] T016 [US2] Refactor `ui/assistant_worker.py` into a runtime bridge that forwards events from `core/assistant_runtime.py`
- [X] T017 [US2] Update `ui/gui_app.py` to consume shared runtime lifecycle events without owning runtime control flow
- [X] T018 [US2] Validate observer-only GUI behavior in `tests/smoke/test_runtime_quickstart.py`

**Checkpoint**: User Story 2 is complete when the GUI acts only as a consumer
of runtime events and removing UI ownership does not change core behavior.

---

## Phase 5: User Story 3 - Shared Lifecycle for Future Work (Priority: P3)

**Goal**: Harden the canonical lifecycle vocabulary and runtime contract so
future phases can build on one stable event model.

**Independent Test**: Verify that startup, standby, wake, setup, listening,
thinking, speaking, error, and offline behavior are emitted consistently and
documented in the runtime contract.

### Tests for User Story 3

- [X] T019 [P] [US3] Add lifecycle vocabulary and transition tests in `tests/unit/test_runtime_contract.py`
- [X] T020 [P] [US3] Add recoverable and offline failure integration tests, including 5-second standby recovery and direct-offline assertions, in `tests/integration/test_runtime_failure_paths.py`

### Implementation for User Story 3

- [X] T021 [US3] Finalize canonical lifecycle states, error transitions, and observer payloads in `core/assistant_runtime.py`
- [X] T022 [US3] Align GUI status mapping and console event handling with the canonical lifecycle in `ui/gui_app.py` and `main.py`
- [X] T023 [US3] Update the runtime contract in `specs/001-runtime-extraction/contracts/runtime-service.md`
- [X] T024 [US3] Re-run and record lifecycle validation guidance in `specs/001-runtime-extraction/quickstart.md`

**Checkpoint**: User Story 3 is complete when the runtime contract, lifecycle
states, and failure rules are stable enough for later speech and capability
work to build on them.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Clean up leftovers and complete cross-story validation.

- [X] T025 [P] Remove leftover UI-owned runtime code paths and cleanup comments in `ui/assistant_worker.py` and `main.py`
- [X] T026 [P] Add any remaining regression coverage in `tests/unit/test_assistant_runtime.py` and `tests/integration/test_runtime_modes.py`
- [X] T027 Measure and document 9-of-10 parity, recoverable-failure timing, and offline-transition behavior in `specs/001-runtime-extraction/quickstart.md`
- [X] T028 Run the full runtime extraction validation sweep, including runtime-log verification and threshold checks, against `specs/001-runtime-extraction/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on User Story 1 because the GUI bridge
  needs the shared runtime behavior to be in place
- **User Story 3 (Phase 5)**: Depends on User Story 1 and benefits from User
  Story 2 being complete so the canonical lifecycle can be hardened across both
  modes
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: First deliverable and MVP - establishes the shared
  runtime service and parity path
- **User Story 2 (P2)**: Builds on US1 by turning the GUI into a pure observer
- **User Story 3 (P3)**: Hardens the lifecycle contract after the shared
  runtime and UI bridge are both in place

### Within Each User Story

- Required tests MUST be written and FAIL before implementation
- Shared runtime and settings changes before observer-specific wiring
- Core implementation before smoke validation and documentation updates
- Logging, failure handling, and validation before the story is considered complete

### Parallel Opportunities

- T005, T006, and T007 can run in parallel after foundational file paths exist
- T008 and T009 can run in parallel for US1
- T014 and T015 can run in parallel for US2
- T019 and T020 can run in parallel for US3
- T025 and T026 can run in parallel during polish

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Add lifecycle and onboarding parity tests in tests/unit/test_assistant_runtime.py"
Task: "Add GUI/console parity integration tests in tests/integration/test_runtime_modes.py"

# Launch independent follow-up work after the runtime loop exists:
Task: "Refactor console startup to use the shared runtime in main.py"
Task: "Align runtime dependency attachment and profile persistence in settings/settings_manager.py and settings/profile_store.py"
```

## Parallel Example: User Story 2

```bash
# Launch all tests for User Story 2 together:
Task: "Add runtime-bridge translation tests in tests/unit/test_assistant_worker.py"
Task: "Add GUI observer integration tests in tests/integration/test_gui_runtime_bridge.py"
```

## Parallel Example: User Story 3

```bash
# Launch all tests for User Story 3 together:
Task: "Add lifecycle vocabulary and transition tests in tests/unit/test_runtime_contract.py"
Task: "Add recoverable and offline failure integration tests in tests/integration/test_runtime_failure_paths.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Confirm GUI and console mode share the same runtime
5. Demo the parity result before moving deeper into UI bridge refinement

### Incremental Delivery

1. Complete Setup + Foundational -> runtime scaffolding ready
2. Add User Story 1 -> validate parity and onboarding -> demo MVP
3. Add User Story 2 -> validate observer-only GUI -> demo debug UI parity
4. Add User Story 3 -> validate lifecycle contract -> prepare for future phases
5. Finish Polish -> run full quickstart validation

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once User Story 1 runtime behavior is in place:
   - Developer A: Console/runtime parity follow-up
   - Developer B: GUI bridge work
   - Developer C: Lifecycle-contract hardening and tests
3. Rejoin for polish and full validation

---

## Notes

- Total tasks: 28
- US1 tasks: 6
- US2 tasks: 5
- US3 tasks: 6
- Suggested MVP scope: Phase 1, Phase 2, and User Story 1 only
- All tasks include checkbox format, task IDs, required story labels for story
  phases, and concrete file paths
- Stop at each checkpoint to validate story behavior independently
