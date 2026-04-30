# Tasks: Capability Refactor

**Input**: Design documents from `/specs/004-capability-refactor/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED because this feature changes resolver, dispatcher, runtime orchestration, controller boundaries, timeout handling, and safety-critical capability behavior.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g. `US1`, `US2`, `US3`)
- Include exact file paths in descriptions

## Path Conventions

- **Current project layout**: `main.py`, `controllers/`, `core/`, `settings/`, `tts/`, `ui/`, `tests/`, `docs/`
- **Feature focus**: `controllers/mock_controllers.py`, `controllers/capability_contracts.py`, `controllers/capability_registry.py`, `controllers/obstacle_controller.py`, `core/resolver.py`, `core/dispatcher.py`, `core/assistant_runtime.py`, `tests/unit/`, `tests/integration/`, `tests/smoke/`
- **Documentation touchpoints**: `specs/004-capability-refactor/contracts/`, `specs/004-capability-refactor/quickstart.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create deterministic capability-test scaffolding and focused validation entry points before changing runtime behavior.

- [X] T001 Add shared capability fixtures, obstacle adapter doubles, and timing helpers in `tests/conftest.py`
- [X] T002 [P] Create unit suites for capability contracts and registry behavior in `tests/unit/test_capability_contracts.py` and `tests/unit/test_capability_registry.py`
- [X] T003 [P] Create obstacle controller and runtime parity suites in `tests/unit/test_obstacle_controller.py` and `tests/integration/test_capability_runtime.py`
- [X] T004 [P] Create smoke validation scenarios for the capability refactor in `tests/smoke/test_capability_refactor_quickstart.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the shared capability contract, registry, and routing scaffolding that every user story depends on.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Add failing contract and timeout coverage for capability descriptors, results, and registry composition in `tests/unit/test_capability_contracts.py` and `tests/unit/test_capability_registry.py`
- [X] T006 Add failing integration coverage for capability dispatch scaffolding in `tests/integration/test_capability_runtime.py`
- [X] T007 Create shared capability descriptors, result models, timeout policies, and handler protocols in `controllers/capability_contracts.py`
- [X] T008 [P] Implement capability registry composition, action bindings, and migrated-vs-fallback metadata helpers in `controllers/capability_registry.py`
- [X] T009 [P] Add shared capability dispatch plumbing and structured result normalization in `core/resolver.py`, `core/dispatcher.py`, and `core/assistant_runtime.py`
- [X] T010 Implement explicit fallback wrappers for unmigrated capabilities in `controllers/mock_controllers.py` and `controllers/capability_registry.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Trust Real Capability Responses (Priority: P1) MVP

**Goal**: Deliver obstacle detection as the first migrated real capability with clear spoken feedback, stable machine-readable results, and GUI or headless parity.

**Independent Test**: Validate obstacle detection as the first migrated real capability in both headless and GUI-assisted runtime paths and confirm it returns the intended spoken guidance, machine-readable outcome, and safe recovery behavior.

### Tests for User Story 1

- [X] T011 [P] [US1] Add unit cases for obstacle adapter availability, idempotent start or stop behavior, status payloads, and safe unavailable outcomes in `tests/unit/test_obstacle_controller.py`
- [X] T012 [P] [US1] Add integration and smoke coverage for console and GUI obstacle flows in `tests/integration/test_capability_runtime.py` and `tests/smoke/test_capability_refactor_quickstart.py`

### Implementation for User Story 1

- [X] T013 [P] [US1] Implement the obstacle adapter boundary and controller start, stop, execute, and status behavior in `controllers/obstacle_controller.py`
- [X] T014 [US1] Register obstacle detection as the first migrated real capability and map existing obstacle intents to registry actions in `controllers/capability_registry.py` and `core/resolver.py`
- [X] T015 [US1] Preserve equivalent obstacle spoken outcomes and machine payloads across runtime modes in `core/dispatcher.py` and `core/assistant_runtime.py`
- [X] T016 [US1] Add obstacle capability observability and concise spoken guidance generation in `controllers/obstacle_controller.py` and `core/assistant_runtime.py`
- [X] T017 [US1] Run obstacle end-to-end regression against `tests/unit/test_obstacle_controller.py`, `tests/integration/test_capability_runtime.py`, and `tests/smoke/test_capability_refactor_quickstart.py` and record `SC-001` and parity notes in `specs/004-capability-refactor/quickstart.md`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently.

---

## Phase 4: User Story 2 - Rely On Consistent Capability Contracts (Priority: P2)

**Goal**: Give runtime consumers one consistent capability contract for migrated and unmigrated capability actions, status snapshots, and idempotent control behavior.

**Independent Test**: Run contract validation across migrated capabilities and confirm action, status, start, and stop behavior return stable, machine-safe outcomes in normal and failure conditions.

### Tests for User Story 2

- [X] T018 [P] [US2] Add contract cases for action bindings, idempotent control requests, and machine-readable status snapshots in `tests/unit/test_capability_contracts.py` and `tests/unit/test_capability_registry.py`
- [X] T019 [P] [US2] Add integration and smoke coverage for status requests and fallback-backed capability actions across runtime paths in `tests/integration/test_capability_runtime.py` and `tests/smoke/test_capability_refactor_quickstart.py`

### Implementation for User Story 2

- [X] T020 [US2] Expand capability result builders for `spoken_text`, `status`, `payload`, and `error_code` parity in `controllers/capability_contracts.py` and `core/dispatcher.py`
- [X] T021 [US2] Register explicit fallback handlers for OCR, money, face, emotion, and system-status capabilities in `controllers/capability_registry.py` and `controllers/mock_controllers.py`
- [X] T022 [US2] Update resolver command-to-capability action mapping and status routing for migrated and fallback capabilities in `core/resolver.py`
- [X] T023 [US2] Enforce idempotent start or stop handling and machine-readable status snapshots across capability handlers in `controllers/obstacle_controller.py` and `controllers/capability_registry.py`
- [X] T024 [US2] Preserve downstream runtime consumption of capability results and snapshots in `core/assistant_runtime.py`
- [X] T025 [US2] Run capability contract regression against `tests/unit/test_capability_contracts.py`, `tests/unit/test_capability_registry.py`, `tests/integration/test_capability_runtime.py`, and `tests/smoke/test_capability_refactor_quickstart.py` and record `SC-002` in `specs/004-capability-refactor/quickstart.md`

**Checkpoint**: At this point, User Stories 1 and 2 should both work independently.

---

## Phase 5: User Story 3 - Keep Runtime Responsive During Capability Failures (Priority: P3)

**Goal**: Enforce capability timeouts, safe failure propagation, and explicit fallback restrictions so a stalled or failing capability never blocks the runtime.

**Independent Test**: Simulate stalled, failing, and partially migrated capability scenarios and confirm timeout handling, safe failure outcomes, and restricted fallback behavior keep the assistant responsive.

### Tests for User Story 3

- [X] T026 [P] [US3] Add unit coverage for timeout expiration, dependency-unavailable results, and migrated-no-fallback rules in `tests/unit/test_obstacle_controller.py` and `tests/unit/test_capability_registry.py`
- [X] T027 [P] [US3] Add integration and smoke coverage for stalled obstacle backends, explicit fallback for unmigrated capabilities, and runtime recovery in `tests/integration/test_capability_runtime.py` and `tests/smoke/test_capability_refactor_quickstart.py`

### Implementation for User Story 3

- [X] T028 [US3] Implement shared timeout execution and failure-result helpers for capability actions in `controllers/capability_contracts.py`, `controllers/capability_registry.py`, and `controllers/obstacle_controller.py`
- [X] T029 [US3] Propagate safe timeout and dependency-failure outcomes through resolver, dispatcher, and runtime recovery paths in `core/resolver.py`, `core/dispatcher.py`, and `core/assistant_runtime.py`
- [X] T030 [US3] Enforce migrated-capability fallback rejection and explicit unmigrated or test-only fallback metadata in `controllers/capability_registry.py` and `controllers/mock_controllers.py`
- [X] T031 [US3] Add structured capability failure logging and recovery timing capture in `core/assistant_runtime.py` and `tests/integration/test_capability_runtime.py`
- [X] T032 [US3] Run capability failure and recovery regression against `tests/unit/test_obstacle_controller.py`, `tests/unit/test_capability_registry.py`, `tests/integration/test_capability_runtime.py`, and `tests/smoke/test_capability_refactor_quickstart.py` and record `SC-003` and timing bounds in `specs/004-capability-refactor/quickstart.md`

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Tighten documentation, cleanup, and end-to-end validation across the refactored capability layer.

- [X] T033 [P] Update capability runtime and obstacle adapter validation notes in `specs/004-capability-refactor/contracts/capability-runtime.md` and `specs/004-capability-refactor/contracts/obstacle-sensor-adapter.md`
- [X] T034 Clean up legacy obstacle routing branches and dead mock-only paths in `controllers/mock_controllers.py`, `core/resolver.py`, `core/dispatcher.py`, and `core/assistant_runtime.py`
- [X] T035 Run the full capability-refactor validation sweep for `tests/unit/test_capability_contracts.py`, `tests/unit/test_capability_registry.py`, `tests/unit/test_obstacle_controller.py`, `tests/integration/test_capability_runtime.py`, and `tests/smoke/test_capability_refactor_quickstart.py` and capture `SC-001`, `SC-002`, `SC-003`, `SC-004`, and baseline metrics in `specs/004-capability-refactor/quickstart.md`
- [X] T036 [P] Run compile validation for `main.py`, `controllers/`, `core/`, `settings/`, `ui/`, and `tests/` with `python -m compileall`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - blocks all user stories
- **User Stories (Phases 3-5)**: Depend on Foundational completion
- **Polish (Phase 6)**: Depends on the user stories you want to ship

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Foundational - no dependency on other user stories
- **User Story 2 (P2)**: Starts after Foundational - builds on the shared capability contract but remains independently testable
- **User Story 3 (P3)**: Starts after Foundational - depends on shared capability routing but remains independently testable

### Within Each User Story

- Write the listed tests first and confirm they fail before implementation
- Finish contract or adapter updates before resolver and runtime wiring
- Finish core implementation before smoke validation and metric capture
- Record quickstart evidence before marking the story done

### Parallel Opportunities

- `T002`, `T003`, and `T004` can run in parallel after `T001`
- `T008` and `T009` can run in parallel after `T007`
- `T011` and `T012` can run in parallel for User Story 1
- `T018` and `T019` can run in parallel for User Story 2
- `T026` and `T027` can run in parallel for User Story 3
- `T033` and `T036` can run in parallel during Polish

---

## Parallel Example: User Story 1

```bash
Task: "Add unit cases for obstacle adapter availability, idempotent start or stop behavior, status payloads, and safe unavailable outcomes in tests/unit/test_obstacle_controller.py"
Task: "Add integration and smoke coverage for console and GUI obstacle flows in tests/integration/test_capability_runtime.py and tests/smoke/test_capability_refactor_quickstart.py"
```

## Parallel Example: User Story 2

```bash
Task: "Add contract cases for action bindings, idempotent control requests, and machine-readable status snapshots in tests/unit/test_capability_contracts.py and tests/unit/test_capability_registry.py"
Task: "Add integration and smoke coverage for status requests and fallback-backed capability actions across runtime paths in tests/integration/test_capability_runtime.py and tests/smoke/test_capability_refactor_quickstart.py"
```

## Parallel Example: User Story 3

```bash
Task: "Add unit coverage for timeout expiration, dependency-unavailable results, and migrated-no-fallback rules in tests/unit/test_obstacle_controller.py and tests/unit/test_capability_registry.py"
Task: "Add integration and smoke coverage for stalled obstacle backends, explicit fallback for unmigrated capabilities, and runtime recovery in tests/integration/test_capability_runtime.py and tests/smoke/test_capability_refactor_quickstart.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate obstacle end-to-end behavior and mode parity before expanding scope

### Incremental Delivery

1. Finish Setup and Foundational to lock the shared capability contract
2. Deliver User Story 1 as the real-capability MVP
3. Add User Story 2 for consistent capability contracts and explicit fallback scaffolding
4. Add User Story 3 for timeout, failure, and fallback hardening
5. Finish with Polish and the full validation sweep

### Parallel Team Strategy

1. One developer completes Setup and shared foundational contracts
2. After Phase 2, separate developers can own User Stories 1, 2, and 3 in parallel
3. Rejoin for Polish, compile validation, and the full regression sweep

---

## Notes

- `[P]` tasks touch different files and can be parallelized safely once their prerequisites are done
- The task list preserves the current command set and focuses on capability routing, contracts, and runtime safety
- Every user story includes explicit test tasks because the feature touches constitution-protected runtime behavior
- `controllers/capability_contracts.py`, `controllers/capability_registry.py`, and `controllers/obstacle_controller.py` are the new implementation modules planned for this feature
