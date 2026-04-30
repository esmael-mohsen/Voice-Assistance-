# Tasks: Wearable Readiness

**Input**: Design documents from `/specs/005-wearable-readiness/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED because this feature changes runtime orchestration, STT/TTS behavior, provider policy, settings application, and safety-critical wearable flows.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g. `US1`, `US2`, `US3`)
- Include exact file paths in descriptions

## Path Conventions

- **Current project layout**: `main.py`, `controllers/`, `core/`, `settings/`, `tts/`, `ui/`, `tests/`, `docs/`
- **Feature focus**: `core/assistant_runtime.py`, `core/stt.py`, `tts/tts_engine.py`, `core/speech/interfaces.py`, `core/speech/provider_registry.py`, `core/speech/provider_resolver.py`, `settings/settings_manager.py`, `settings/profile_store.py`, `tests/unit/`, `tests/integration/`, `tests/smoke/`
- **Documentation touchpoints**: `specs/005-wearable-readiness/contracts/`, `specs/005-wearable-readiness/quickstart.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create deterministic validation scaffolding before changing runtime behavior.

- [X] T001 Add wearable runtime fixtures for fake timing, network state, and wake signal inputs in `tests/conftest.py`
- [X] T002 [P] Create unit-test modules for wearable runtime behavior in `tests/unit/test_runtime_interrupt_preemption.py`, `tests/unit/test_offline_allowlist_policy.py`, and `tests/unit/test_wearable_priority_feedback.py`
- [X] T003 [P] Create integration-test modules for runtime wearable journeys in `tests/integration/test_runtime_interruptions.py`, `tests/integration/test_runtime_offline_behavior.py`, and `tests/integration/test_wearable_startup_readiness.py`
- [X] T004 [P] Create smoke validation entry for wearable readiness in `tests/smoke/test_wearable_readiness_quickstart.py` and link execution notes in `specs/005-wearable-readiness/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared contracts and policy primitives required by all user stories.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Add failing baseline coverage for wearable runtime event/result contract fields in `tests/unit/test_runtime_contract.py` and `tests/unit/test_assistant_runtime.py`
- [X] T006 [P] Add failing provider metadata and degraded resolution tests in `tests/unit/test_provider_registry.py` and `tests/unit/test_provider_resolver.py`
- [X] T007 Implement shared wearable runtime models for priority events, speech windows, and recovery outcomes in `core/command_models.py`
- [X] T008 [P] Implement authoritative provider-network metadata and offline policy helpers in `core/speech/interfaces.py`, `core/speech/provider_registry.py`, and `core/speech/provider_resolver.py`
- [X] T009 Implement runtime observability scaffolding for priority/coalescing/interruption/offline/startup fields in `core/assistant_runtime.py` and `core/dispatcher.py`
- [X] T010 [P] Add configurable wearable session bounds and persistence keys in `settings/settings_manager.py`, `settings/profile_store.py`, and `settings/user_profile.json`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Interrupt And Recover Safely (Priority: P1) MVP

**Goal**: Ensure stop/cancel/emergency can preempt active listening/speaking with bounded session behavior and explicit recovery outcomes.

**Independent Test**: Run interruption-focused scenarios where listening or speaking is active and verify preemption timing plus safe timeout recovery.

### Tests for User Story 1

- [X] T011 [P] [US1] Add unit tests for stop/cancel/emergency preemption and non-critical speech discard behavior in `tests/unit/test_runtime_interrupt_preemption.py`
- [X] T012 [P] [US1] Add integration tests for interruption latency and timeout recovery during live runtime cycles in `tests/integration/test_runtime_interruptions.py`

### Implementation for User Story 1

- [X] T013 [US1] Implement interruption signal handling and preemption state transitions in `core/assistant_runtime.py`
- [X] T014 [US1] Implement bounded listening windows with timeout outcomes in `core/stt.py` and `core/assistant_runtime.py`
- [X] T015 [P] [US1] Implement bounded speaking session controls and interrupt hooks in `tts/tts_engine.py` and `settings/settings_manager.py`
- [X] T016 [US1] Emit machine-readable interruption/timeout recovery outcomes in `core/assistant_runtime.py` and `core/command_models.py`
- [X] T017 [US1] Run US1 validation via `tests/unit/test_runtime_interrupt_preemption.py` and `tests/integration/test_runtime_interruptions.py` and record SC-002 evidence in `specs/005-wearable-readiness/quickstart.md`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently.

---

## Phase 4: User Story 2 - Stay Usable In Weak Or Offline Conditions (Priority: P2)

**Goal**: Enforce deterministic offline/degraded behavior using authoritative `requires_network` metadata and allowlist-only local fallback.

**Independent Test**: Simulate weak-network/offline conditions and verify safe refusal or explicit allowlisted fallback behavior for network-sensitive actions.

### Tests for User Story 2

- [X] T018 [P] [US2] Add unit tests for `requires_network` enforcement and allowlist-only fallback decisions in `tests/unit/test_offline_allowlist_policy.py` and `tests/unit/test_provider_registry.py`
- [X] T019 [P] [US2] Add integration tests for runtime offline/degraded decisions and guidance messaging in `tests/integration/test_runtime_offline_behavior.py`

### Implementation for User Story 2

- [X] T020 [US2] Implement offline allowlist evaluation helpers and decision payloads in `core/speech/provider_resolver.py` and `settings/settings_manager.py`
- [X] T021 [P] [US2] Enforce authoritative provider `requires_network` metadata in `core/speech/interfaces.py` and `core/speech/provider_registry.py`
- [X] T022 [US2] Implement runtime execution gating for allowlisted fallback vs safe refusal in `core/assistant_runtime.py` and `core/resolver.py`
- [X] T023 [US2] Add concise offline next-step guidance and degraded observability fields in `core/assistant_runtime.py` and `settings/settings_manager.py`
- [X] T024 [US2] Run US2 validation via `tests/unit/test_offline_allowlist_policy.py` and `tests/integration/test_runtime_offline_behavior.py` and record SC-003 evidence in `specs/005-wearable-readiness/quickstart.md`

**Checkpoint**: At this point, User Stories 1 and 2 should both work independently.

---

## Phase 5: User Story 3 - Use Wearable-Friendly Feedback Without Screen Dependence (Priority: P3)

**Goal**: Deliver concise priority-aware output, startup/standby readiness signals, wearable wake defaults, and critical bilingual prompt integrity.

**Independent Test**: Validate priority ordering/coalescing, startup readiness timing, standby responsiveness, wake fallback behavior, and critical prompt integrity in headless flows.

### Tests for User Story 3

- [X] T025 [P] [US3] Add unit tests for priority ordering, 2-second coalescing, concise response limits, and non-speech cue mapping in `tests/unit/test_wearable_priority_feedback.py`
- [X] T026 [P] [US3] Add integration tests for startup readiness milestones, standby wake responsiveness, and supported-hardware non-speech cue emission in `tests/integration/test_wearable_startup_readiness.py`
- [X] T027 [P] [US3] Add smoke coverage for end-to-end wearable readiness flows in `tests/smoke/test_wearable_readiness_quickstart.py`

### Implementation for User Story 3

- [X] T028 [US3] Implement priority routing and same-priority duplicate coalescing (2 seconds) in `core/assistant_runtime.py`
- [X] T029 [US3] Implement wearable wake policy defaults and dev-only STT wake fallback guardrails in `core/assistant_runtime.py` and `core/speech/provider_resolver.py`
- [X] T030 [US3] Implement startup readiness snapshots, low-power standby signaling, and non-speech cue state hooks in `core/assistant_runtime.py`
- [X] T031 [US3] Add critical Arabic/English prompt catalog checks and corruption-safe fallback before speech output in `settings/settings_manager.py` and `core/assistant_runtime.py`
- [X] T032 [US3] Run US3 validation via `tests/unit/test_wearable_priority_feedback.py`, `tests/integration/test_wearable_startup_readiness.py`, and `tests/smoke/test_wearable_readiness_quickstart.py` and record SC-001/SC-004/SC-005/SC-006/SC-007 evidence in `specs/005-wearable-readiness/quickstart.md`

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final hardening, documentation alignment, and full validation sweep.

- [X] T033 [P] Update finalized runtime/provider contract examples in `specs/005-wearable-readiness/contracts/wearable-runtime-contract.md` and `specs/005-wearable-readiness/contracts/provider-readiness-contract.md`
- [X] T034 Consolidate wearable observability keys and remove obsolete non-wearable runtime branches in `core/assistant_runtime.py`, `core/speech/provider_resolver.py`, and `settings/settings_manager.py`
- [X] T035 [P] Extend cross-cutting regression for provider persistence and GUI bridge parity in `tests/unit/test_settings_provider_persistence.py` and `tests/integration/test_gui_runtime_bridge.py`
- [X] T036 Run full validation sweep (`pytest tests/unit`, `pytest tests/integration`, `pytest tests/smoke`) and capture results in `specs/005-wearable-readiness/quickstart.md`
- [X] T037 Run compile validation (`python -m compileall main.py core settings tts ui tests`) and capture output notes in `specs/005-wearable-readiness/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - blocks all user stories
- **User Stories (Phases 3-5)**: Depend on Foundational completion
- **Polish (Phase 6)**: Depends on the user stories selected for release scope

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Foundational - no dependency on other user stories
- **User Story 2 (P2)**: Starts after Foundational - remains independently testable from US1
- **User Story 3 (P3)**: Starts after Foundational - remains independently testable from US1 and US2

### Within Each User Story

- Write listed tests first and confirm they fail before implementation
- Complete runtime/policy implementation before story-level validation runs
- Record quickstart evidence before marking story completion

### Parallel Opportunities

- `T002`, `T003`, and `T004` can run in parallel after `T001`
- `T006`, `T008`, and `T010` can run in parallel after `T005` and `T007`
- `T011` and `T012` can run in parallel for User Story 1
- `T018` and `T019` can run in parallel for User Story 2
- `T025`, `T026`, and `T027` can run in parallel for User Story 3
- `T033` and `T035` can run in parallel during Polish

---

## Parallel Example: User Story 1

```bash
Task: "Add unit tests for stop/cancel/emergency preemption and non-critical speech discard behavior in tests/unit/test_runtime_interrupt_preemption.py"
Task: "Add integration tests for interruption latency and timeout recovery during live runtime cycles in tests/integration/test_runtime_interruptions.py"
```

## Parallel Example: User Story 2

```bash
Task: "Add unit tests for requires_network enforcement and allowlist-only fallback decisions in tests/unit/test_offline_allowlist_policy.py and tests/unit/test_provider_registry.py"
Task: "Add integration tests for runtime offline/degraded decisions and guidance messaging in tests/integration/test_runtime_offline_behavior.py"
```

## Parallel Example: User Story 3

```bash
Task: "Add unit tests for priority ordering, 2-second coalescing, concise response limits, and non-speech cue mapping in tests/unit/test_wearable_priority_feedback.py"
Task: "Add integration tests for startup readiness milestones, standby wake responsiveness, and supported-hardware non-speech cue emission in tests/integration/test_wearable_startup_readiness.py"
Task: "Add smoke coverage for end-to-end wearable readiness flows in tests/smoke/test_wearable_readiness_quickstart.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate interruption and bounded-session behavior before expanding scope

### Incremental Delivery

1. Complete Setup + Foundational to lock shared runtime/provider policy scaffolding
2. Deliver User Story 1 (safe interruption/recovery)
3. Deliver User Story 2 (offline/degraded safety policy)
4. Deliver User Story 3 (priority feedback and startup/standby readiness)
5. Complete Polish and full validation sweep

### Parallel Team Strategy

1. Team aligns on Setup and Foundational phases first
2. After Phase 2:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Rejoin for Phase 6 polish and release validation

---

## Notes

- `[P]` tasks are parallel-safe only after their dependencies are complete
- Every user story includes test tasks because this feature touches constitution-protected runtime behavior
- Keep headless-first behavior as the reference during implementation and validation
- Record SC evidence directly in `specs/005-wearable-readiness/quickstart.md` as tasks complete
