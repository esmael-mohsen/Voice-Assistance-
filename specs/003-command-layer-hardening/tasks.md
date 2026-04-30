# Tasks: Command Layer Hardening

**Input**: Design documents from `/specs/003-command-layer-hardening/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED because this feature changes parser, resolver, dispatcher, runtime orchestration, and safety-critical command handling.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g. US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Current project layout**: `main.py`, `controllers/`, `core/`, `settings/`, `ui/`, `tests/`, `docs/`
- **Feature focus**: `core/parser.py`, `core/resolver.py`, `core/dispatcher.py`, `core/assistant_runtime.py`, `controllers/mock_controllers.py`, `tests/unit/`, `tests/integration/`, `tests/smoke/`
- **New module for this feature**: `core/command_models.py`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create shared regression scaffolding and focused command-test entry points before changing runtime behavior.

- [X] T001 Add shared bilingual command fixtures, scripted command outcomes, and helper doubles in `tests/conftest.py`
- [X] T002 [P] Create parser and resolver regression suites in `tests/unit/test_parser.py` and `tests/unit/test_resolver.py`
- [X] T003 [P] Create structured dispatch and smoke validation suites in `tests/integration/test_command_dispatch.py` and `tests/smoke/test_command_layer_quickstart.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the shared command contract and runtime plumbing that every user story depends on.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Create shared command dataclasses and one-turn session context models in `core/command_models.py`
- [X] T005 Protect the shared parse, resolve, and dispatch contract in `tests/unit/test_parser.py`, `tests/unit/test_resolver.py`, and `tests/integration/test_command_dispatch.py`
- [X] T006 [P] Replace the raw keyword map with categorized command metadata and validation profiles in `core/parser.py`
- [X] T007 [P] Add structured rejected and failed result helpers plus command-outcome metadata in `core/dispatcher.py`
- [X] T008 Update runtime normalization and observability for structured command results in `core/assistant_runtime.py` and `tests/unit/test_assistant_runtime.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Trust Everyday Commands (Priority: P1) MVP

**Goal**: Make common Arabic and English commands resolve reliably while safely rejecting near-miss phrases.

**Independent Test**: Run curated bilingual regressions across everyday assistant commands, highest-value capability commands, and protected-system near-miss phrases and confirm intended commands succeed while weak matches are rejected in both GUI and console flows.

### Tests for User Story 1

- [X] T009 [P] [US1] Add bilingual acceptance and near-miss parser cases in `tests/unit/test_parser.py`
- [X] T010 [P] [US1] Add dispatch and smoke parity coverage for everyday assistant, highest-value capability, and protected-system near-miss commands in `tests/integration/test_command_dispatch.py` and `tests/smoke/test_command_layer_quickstart.py`

### Implementation for User Story 1

- [X] T011 [US1] Implement accepted, ambiguous, and rejected parse decisions with ambiguity margins for capability and settings commands in `core/parser.py`
- [X] T012 [US1] Update everyday command routing for capability and settings intents in `core/resolver.py` and `controllers/mock_controllers.py`
- [X] T013 [US1] Preserve equivalent spoken outcomes for everyday commands across runtime modes in `core/assistant_runtime.py` and `tests/integration/test_runtime_modes.py`
- [X] T014 [US1] Add matched and rejected command logging for everyday flows in `core/dispatcher.py`
- [X] T015 [US1] Run bilingual trust regression for everyday assistant, obstacle, OCR, face, emotion, money, and protected-system boundary cases against `tests/unit/test_parser.py`, `tests/integration/test_command_dispatch.py`, `tests/integration/test_runtime_modes.py`, and `tests/smoke/test_command_layer_quickstart.py` and record the curated pass-rate metric for `SC-001`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently.

---

## Phase 4: User Story 2 - Return Structured Command Outcomes (Priority: P2)

**Goal**: Return structured command results with normalized parameters, one-turn clarification, and one-turn follow-up context for downstream consumers.

**Independent Test**: Execute representative commands with valid parameters, missing parameters, and a one-turn face-to-emotion follow-up and confirm each returns a stable structured outcome.

### Tests for User Story 2

- [X] T016 [P] [US2] Add resolver cases for structured parameters, clarification, and one-turn follow-up context in `tests/unit/test_resolver.py`
- [X] T017 [P] [US2] Add dispatch and runtime contract cases for success, clarification, rejection, and consumed follow-up metadata in `tests/integration/test_command_dispatch.py` and `tests/unit/test_assistant_runtime.py`

### Implementation for User Story 2

- [X] T018 [US2] Expand resolution models and helper constructors for parameters, status, payload, and error codes in `core/command_models.py` and `core/resolver.py`
- [X] T019 [US2] Implement one-shot clarification and face-to-emotion follow-up handling in `core/resolver.py`
- [X] T020 [US2] Return unified `CommandExecutionResult` payloads and metadata from `core/dispatcher.py`
- [X] T021 [US2] Update machine-readable face follow-up data production in `controllers/mock_controllers.py` and `core/resolver.py`
- [X] T022 [US2] Preserve structured dispatch results for downstream consumers and logs in `core/assistant_runtime.py`
- [X] T023 [US2] Run structured outcome regression against `tests/unit/test_resolver.py`, `tests/integration/test_command_dispatch.py`, and `tests/unit/test_assistant_runtime.py`

**Checkpoint**: At this point, User Stories 1 and 2 should both work independently.

---

## Phase 5: User Story 3 - Separate Safe System Commands (Priority: P3)

**Goal**: Route system commands through stricter safety rules, including explicit confirmation for protected actions and stronger validation for lower-risk system actions.

**Independent Test**: Validate protected system commands, lower-risk system commands, and ambiguous risky phrases and confirm risky actions only execute through explicit confirmation or strong matches.

### Tests for User Story 3

- [X] T024 [P] [US3] Add protected and elevated system-command parse safety cases in `tests/unit/test_parser.py`
- [X] T025 [P] [US3] Add confirmation-flow dispatch and smoke coverage for risky system commands, including zero-unintended-activation boundary cases, in `tests/integration/test_command_dispatch.py` and `tests/smoke/test_command_layer_quickstart.py`

### Implementation for User Story 3

- [X] T026 [US3] Classify system intents by elevated and protected risk and apply stricter parser thresholds in `core/parser.py`
- [X] T027 [US3] Implement `confirmation_required` resolution, one-turn expiry, and safe rejection for `stop_system` and `reset_settings` in `core/resolver.py` and `core/command_models.py`
- [X] T028 [US3] Keep system-command routing and audit metadata separate from capability routing in `core/dispatcher.py` and `core/assistant_runtime.py`
- [X] T029 [US3] Update system controller stubs and runtime parity assertions for confirmed versus rejected risky commands in `controllers/mock_controllers.py` and `tests/integration/test_runtime_modes.py`
- [X] T030 [US3] Run protected-command safety regression against `tests/unit/test_parser.py`, `tests/integration/test_command_dispatch.py`, `tests/integration/test_runtime_modes.py`, and `tests/smoke/test_command_layer_quickstart.py` and record the zero-unintended-activation metric for `SC-002`

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Tighten documentation, cleanup, and end-to-end validation across the hardened command layer.

- [X] T031 [P] Update command contract and quickstart validation notes for degraded-mode behavior and latency-baseline capture in `specs/003-command-layer-hardening/contracts/command-processing-runtime.md` and `specs/003-command-layer-hardening/quickstart.md`
- [X] T032 Clean up command-layer logging and dead branches in `core/parser.py`, `core/resolver.py`, `core/dispatcher.py`, and `core/assistant_runtime.py`
- [X] T033 Run the full command-hardening regression sweep for `tests/unit/test_parser.py`, `tests/unit/test_resolver.py`, `tests/integration/test_command_dispatch.py`, `tests/integration/test_runtime_modes.py`, `tests/unit/test_assistant_runtime.py`, and `tests/smoke/test_command_layer_quickstart.py` and capture `SC-001`, `SC-002`, `SC-003`, `SC-004`, and wake/STT/TTS/dispatch/recovery baseline metrics
- [X] T034 [P] Run compile validation for `main.py`, `core/`, `settings/`, `ui/`, and `tests/` with `python -m compileall`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - blocks all user stories
- **User Stories (Phases 3-5)**: Depend on Foundational completion
- **Polish (Phase 6)**: Depends on the user stories you want to ship

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Foundational - no dependency on other user stories
- **User Story 2 (P2)**: Starts after Foundational - uses the shared command contract but remains independently testable
- **User Story 3 (P3)**: Starts after Foundational - uses the shared command contract but remains independently testable

### Within Each User Story

- Write the listed tests first and confirm they fail before implementation
- Finish parser and model changes before resolver and dispatcher wiring
- Finish resolver and dispatcher behavior before runtime parity and smoke validation
- Complete regression runs before marking the story done

### Parallel Opportunities

- `T002` and `T003` can run in parallel after `T001`
- `T006` and `T007` can run in parallel after `T004` and `T005`
- `T009` and `T010` can run in parallel for User Story 1
- `T016` and `T017` can run in parallel for User Story 2
- `T024` and `T025` can run in parallel for User Story 3
- `T031` and `T034` can run in parallel during Polish

---

## Parallel Example: User Story 1

```bash
Task: "Add bilingual acceptance and near-miss parser cases in tests/unit/test_parser.py"
Task: "Add dispatch and smoke parity coverage for everyday assistant commands in tests/integration/test_command_dispatch.py and tests/smoke/test_command_layer_quickstart.py"
```

## Parallel Example: User Story 2

```bash
Task: "Add resolver cases for structured parameters, clarification, and one-turn follow-up context in tests/unit/test_resolver.py"
Task: "Add dispatch and runtime contract cases for success, clarification, rejection, and consumed follow-up metadata in tests/integration/test_command_dispatch.py and tests/unit/test_assistant_runtime.py"
```

## Parallel Example: User Story 3

```bash
Task: "Add protected and elevated system-command parse safety cases in tests/unit/test_parser.py"
Task: "Add confirmation-flow dispatch and smoke coverage for risky system commands in tests/integration/test_command_dispatch.py and tests/smoke/test_command_layer_quickstart.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate the bilingual trust regression for User Story 1 before expanding scope

### Incremental Delivery

1. Finish Setup and Foundational to lock the shared command contract
2. Deliver User Story 1 as the trust-focused MVP
3. Add User Story 2 for structured outcomes and one-turn follow-up context
4. Add User Story 3 for protected system-command safeguards
5. Finish with Polish and the full regression sweep

### Parallel Team Strategy

1. One developer completes Setup and shared foundational contracts
2. After Phase 2, separate developers can own User Stories 1, 2, and 3 in parallel
3. Rejoin for Polish, compile validation, and the full regression sweep

---

## Notes

- `[P]` tasks touch different files and can be parallelized safely once their prerequisites are done
- The task list stays within the current supported command set and does not add new intents
- Every user story includes explicit test tasks because the feature touches safety-sensitive runtime behavior
- `core/command_models.py` is the only new top-level feature module planned for this work

