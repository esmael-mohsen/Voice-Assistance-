---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED when the feature touches parser, resolver,
dispatcher, runtime orchestration, settings application, provider adapters, or
safety-critical behavior. Other test tasks may still be added when the feature
specification requests them.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Current project layout**: `main.py`, `controllers/`, `core/`, `settings/`,
  `tts/`, `ui/`, `tests/`, `docs/`
- **New architecture slices**: add `runtime/` or `capabilities/` only when the
  plan justifies a new top-level package
- Always use real repository paths from `plan.md`

<!--
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.

  The /speckit.tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/

  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as an MVP increment

  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create or confirm project structure per implementation plan
- [ ] T002 Create shared test scaffolding in tests/
- [ ] T003 [P] Create shared logging or observability scaffolding for touched flows
- [ ] T004 [P] Document smoke validation entry points for console, headless, or GUI debug paths

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

Examples of foundational tasks (adjust based on your project):

- [ ] T005 Define or update interfaces for runtime, provider, or capability boundaries
- [ ] T006 [P] Add fallback and timeout handling for affected providers or integrations
- [ ] T007 [P] Create structured result helpers for `spoken_text`, `status`, `payload`, and `error_code`
- [ ] T008 Protect touched parser, resolver, dispatcher, or settings logic with automated tests
- [ ] T009 Configure latency, reliability, or failure-path validation for the feature

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) MVP

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 1

> **NOTE: Write these tests FIRST and ensure they fail before implementation
> when this story touches constitution-protected runtime areas**

- [ ] T010 [P] [US1] Add unit or contract tests for changed command, adapter, or capability behavior
- [ ] T011 [P] [US1] Add integration or smoke validation for the user journey

### Implementation for User Story 1

- [ ] T012 [P] [US1] Implement or update feature code in the planned repository paths
- [ ] T013 [P] [US1] Add or update structured result handling
- [ ] T014 [US1] Add validation, fallback, and error handling
- [ ] T015 [US1] Add logging for user story operations
- [ ] T016 [US1] Validate accessibility and spoken response behavior
- [ ] T017 [US1] Run and record the planned smoke validation

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 2

- [ ] T018 [P] [US2] Add unit or contract tests for changed behavior
- [ ] T019 [P] [US2] Add integration or smoke validation for the user journey

### Implementation for User Story 2

- [ ] T020 [P] [US2] Implement or update feature code in the planned repository paths
- [ ] T021 [US2] Add validation, fallback, and error handling
- [ ] T022 [US2] Add logging and observability updates
- [ ] T023 [US2] Run and record the planned smoke validation

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 3

- [ ] T024 [P] [US3] Add unit or contract tests for changed behavior
- [ ] T025 [P] [US3] Add integration or smoke validation for the user journey

### Implementation for User Story 3

- [ ] T026 [P] [US3] Implement or update feature code in the planned repository paths
- [ ] T027 [US3] Add validation, fallback, and error handling
- [ ] T028 [US3] Run and record the planned smoke validation

**Checkpoint**: All user stories should now be independently functional

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] TXXX [P] Documentation updates in docs/
- [ ] TXXX Code cleanup and refactoring
- [ ] TXXX Performance and latency validation across affected flows
- [ ] TXXX [P] Additional automated tests in tests/unit/, tests/integration/, or tests/contract/
- [ ] TXXX Degraded-mode validation for network loss, provider failure, or noisy input
- [ ] TXXX Run quickstart.md or equivalent smoke validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 -> P2 -> P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Required tests MUST be written and FAIL before implementation
- Interface or schema updates before provider-specific implementation
- Core implementation before integration and polish
- Logging, fallback, and smoke validation before the story is considered complete

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Independent implementation tasks within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Add unit or contract tests for changed behavior"
Task: "Add integration or smoke validation for the user journey"

# Launch independent implementation tasks together:
Task: "Implement feature code in the planned repository paths"
Task: "Add structured result handling"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational -> Foundation ready
2. Add User Story 1 -> Test independently -> Deploy/Demo (MVP!)
3. Add User Story 2 -> Test independently -> Deploy/Demo
4. Add User Story 3 -> Test independently -> Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify required tests fail before implementing
- Include observability, fallback, and smoke validation where the constitution requires them
- Stop at any checkpoint to validate the story independently
- Avoid vague tasks, same-file conflicts, and cross-story dependencies that break independence
