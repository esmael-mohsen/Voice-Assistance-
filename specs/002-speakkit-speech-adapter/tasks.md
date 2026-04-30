# Tasks: Speech Abstraction and SpeakKit Adapter

**Input**: Design documents from `/specs/002-speakkit-speech-adapter/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED because this feature touches runtime
orchestration, settings persistence, provider adapters, fallback safety, and
observer payload behavior.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Current project layout**: `main.py`, `controllers/`, `core/`, `settings/`,
  `tts/`, `ui/`, `tests/`, `docs/`
- **New architecture slices**: add provider adapters under `core/speech/`
- Always use real repository paths from `plan.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create baseline scaffolding for provider-abstraction development
and validation.

- [X] T001 Create speech-provider package scaffolding in `core/speech/__init__.py` and `core/speech/interfaces.py`
- [X] T002 Create provider test package scaffolding in `tests/unit/__init__.py`, `tests/integration/__init__.py`, and `tests/smoke/__init__.py`
- [X] T003 [P] Add shared provider fixtures and doubles in `tests/conftest.py`
- [X] T004 [P] Add smoke validation scaffold for provider matrix scenarios in `tests/smoke/test_speech_provider_quickstart.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared provider-selection and persistence foundations
required by all user stories.

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Define provider service contracts for wake/STT/TTS in `core/speech/interfaces.py`
- [X] T006 Implement provider registry and availability model in `core/speech/provider_registry.py`
- [X] T007 [P] Implement provider resolver and fallback-policy helpers in `core/speech/provider_resolver.py`
- [X] T008 [P] Extend persisted settings/profile schema for provider selection and deferred switching in `settings/settings_manager.py` and `settings/profile_store.py`
- [X] T009 [P] Add foundational unit coverage for provider registry, resolver rules, and settings persistence in `tests/unit/test_provider_registry.py`, `tests/unit/test_provider_resolver.py`, and `tests/unit/test_settings_provider_persistence.py`
- [X] T010 Add baseline runtime event payload support for provider metadata in `core/assistant_runtime.py`

**Checkpoint**: Foundation ready - provider abstraction, persistence, and
resolver rules exist for story implementation.

---

## Phase 3: User Story 1 - Preserve Stable Speech Experience (Priority: P1) MVP

**Goal**: Preserve current legacy speech behavior through the new provider
abstraction without requiring SpeakKit.

**Independent Test**: Start GUI and console runtime with legacy/default provider
and verify wake + command flows remain behaviorally equivalent to the baseline.

### Tests for User Story 1

- [X] T011 [P] [US1] Add legacy-provider parity unit tests in `tests/unit/test_legacy_provider_parity.py`
- [X] T012 [P] [US1] Add legacy runtime integration parity tests in `tests/integration/test_legacy_provider_runtime.py`

### Implementation for User Story 1

- [X] T013 [P] [US1] Implement legacy adapter wrappers in `core/speech/legacy_stt.py`, `core/speech/legacy_tts.py`, and `core/speech/legacy_wake.py`
- [X] T014 [US1] Integrate legacy provider resolution into shared runtime startup and command loop in `core/assistant_runtime.py`
- [X] T015 [US1] Align default provider selection loading with runtime settings in `settings/settings_manager.py` and `settings/profile_store.py`
- [X] T016 [US1] Validate configured legacy-path smoke scenarios in `tests/smoke/test_speech_provider_quickstart.py`

**Checkpoint**: User Story 1 is complete when legacy behavior is preserved
through the provider-abstraction path in both GUI and console modes.

---

## Phase 4: User Story 2 - Enable SpeakKit as Selectable Provider (Priority: P2)

**Goal**: Enable SpeakKit as a selectable and persisted provider with
restart-only switch semantics.

**Independent Test**: Persist provider mode as SpeakKit, run representative GUI
and console flows, request provider switch while active, and verify switch is
deferred until restart.

### Tests for User Story 2

- [X] T017 [P] [US2] Add provider-selection persistence and restart-only switch unit tests in `tests/unit/test_provider_selection.py`
- [X] T018 [P] [US2] Add SpeakKit path integration tests across GUI and console observers in `tests/integration/test_speakkit_provider_runtime.py`

### Implementation for User Story 2

- [X] T019 [P] [US2] Implement SpeakKit adapters in `core/speech/speakkit_stt.py`, `core/speech/speakkit_tts.py`, and `core/speech/speakkit_wake.py`
- [X] T020 [US2] Integrate SpeakKit provider registration and restart-time deferred-switch application in `core/speech/provider_registry.py`, `core/speech/provider_resolver.py`, and `core/assistant_runtime.py`
- [X] T021 [US2] Surface persisted provider state through settings and observer-facing config events in `settings/settings_manager.py`, `main.py`, and `ui/gui_app.py`
- [X] T022 [US2] Validate SpeakKit selection and restart-only switching smoke scenarios in `tests/smoke/test_speech_provider_quickstart.py`

**Checkpoint**: User Story 2 is complete when SpeakKit can be selected and
persisted safely, with deferred switch behavior enforced.

---

## Phase 5: User Story 3 - Recover Safely from Provider Failures (Priority: P3)

**Goal**: Enforce directional fallback, startup degradation behavior, and
offline safety when both providers are unavailable.

**Independent Test**: Simulate startup/provider failures and verify:
SpeakKit->legacy fallback, legacy no-auto-switch, startup degraded legacy with
persisted provider unchanged, and dual-provider offline transition.

### Tests for User Story 3

- [X] T023 [P] [US3] Add directional fallback-policy unit tests in `tests/unit/test_provider_fallback_policy.py`
- [X] T024 [P] [US3] Add startup degradation and dual-provider offline integration tests in `tests/integration/test_provider_failure_paths.py`

### Implementation for User Story 3

- [X] T025 [US3] Implement SpeakKit->legacy fallback and legacy no-auto-switch enforcement in `core/speech/provider_resolver.py` and `core/assistant_runtime.py`
- [X] T026 [US3] Implement persisted-provider-unavailable startup degradation handling in `core/assistant_runtime.py` and `settings/settings_manager.py`
- [X] T027 [US3] Implement dual-provider unavailable transition to offline with manual-restart requirement in `core/assistant_runtime.py`
- [X] T028 [US3] Emit provider-aware degraded-mode and fallback observability payloads in `core/assistant_runtime.py` and `ui/assistant_worker.py`
- [X] T029 [US3] Validate full failure-safety matrix smoke scenarios in `tests/smoke/test_speech_provider_quickstart.py`

**Checkpoint**: User Story 3 is complete when fallback/degradation/offline
safety rules are consistently enforced and observable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finalize docs, regressions, and end-to-end validation.

- [X] T030 [P] Update provider contract and quickstart validation guidance in `specs/002-speakkit-speech-adapter/contracts/speech-provider-runtime.md` and `specs/002-speakkit-speech-adapter/quickstart.md`
- [X] T031 Add regression coverage for provider payload compatibility in `tests/unit/test_assistant_runtime.py` and `tests/integration/test_runtime_modes.py`
- [X] T032 [P] Perform cleanup and consistency pass across `core/speech/*.py`, `settings/settings_manager.py`, and `core/assistant_runtime.py`
- [X] T033 Run full validation sweep (compile, unit, integration, smoke) and record outcomes in `specs/002-speakkit-speech-adapter/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on User Story 1 foundations to preserve baseline while adding SpeakKit
- **User Story 3 (Phase 5)**: Depends on User Story 1 and User Story 2 provider paths being in place
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: First deliverable and MVP - preserves legacy behavior through abstraction
- **User Story 2 (P2)**: Builds on US1 to add selectable/persisted SpeakKit mode
- **User Story 3 (P3)**: Builds on US1+US2 to enforce failure safety and fallback direction

### Within Each User Story

- Required tests MUST be written and FAIL before implementation
- Provider adapter/selection wiring before scenario-specific observability polish
- Core implementation before smoke validation and checkpoint sign-off
- Runtime safety and degraded-mode behavior must be validated before story closure

### Parallel Opportunities

- T003 and T004 can run in parallel in Setup
- T007, T008, and T009 can run in parallel in Foundational phase
- T011 and T012 can run in parallel for US1
- T013 can proceed in parallel across three legacy adapter files
- T017 and T018 can run in parallel for US2
- T019 can proceed in parallel across three SpeakKit adapter files
- T023 and T024 can run in parallel for US3
- T030 and T032 can run in parallel during Polish

---

## Parallel Example: User Story 1

```bash
# Launch tests for User Story 1 together:
Task: "Add legacy-provider parity unit tests in tests/unit/test_legacy_provider_parity.py"
Task: "Add legacy runtime integration parity tests in tests/integration/test_legacy_provider_runtime.py"

# Launch adapter implementation tasks together:
Task: "Implement legacy STT adapter in core/speech/legacy_stt.py"
Task: "Implement legacy TTS adapter in core/speech/legacy_tts.py"
Task: "Implement legacy wake adapter in core/speech/legacy_wake.py"
```

## Parallel Example: User Story 2

```bash
# Launch tests for User Story 2 together:
Task: "Add provider-selection persistence and restart-only switch unit tests in tests/unit/test_provider_selection.py"
Task: "Add SpeakKit path integration tests in tests/integration/test_speakkit_provider_runtime.py"

# Launch SpeakKit adapter implementation together:
Task: "Implement SpeakKit STT adapter in core/speech/speakkit_stt.py"
Task: "Implement SpeakKit TTS adapter in core/speech/speakkit_tts.py"
Task: "Implement SpeakKit wake adapter in core/speech/speakkit_wake.py"
```

## Parallel Example: User Story 3

```bash
# Launch tests for User Story 3 together:
Task: "Add directional fallback-policy unit tests in tests/unit/test_provider_fallback_policy.py"
Task: "Add startup degradation and dual-provider offline integration tests in tests/integration/test_provider_failure_paths.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Confirm legacy behavior parity through abstraction in GUI and console
5. Demo baseline-preserving architecture before enabling SpeakKit path

### Incremental Delivery

1. Setup + Foundational -> provider abstraction base ready
2. Add User Story 1 -> verify baseline parity -> demo MVP
3. Add User Story 2 -> verify selectable/persisted SpeakKit and restart-only switch
4. Add User Story 3 -> verify fallback/degradation/offline safety matrix
5. Finish Polish -> run complete quickstart validation

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. After foundation is ready:
   - Developer A: Legacy adapter and parity completion (US1 support)
   - Developer B: SpeakKit adapters and selection flow (US2)
   - Developer C: Failure-path policy and safety validation (US3)
3. Rejoin for polish, regression sweep, and release-readiness validation

---

## Notes

- Total tasks: 33
- US1 tasks: 6
- US2 tasks: 6
- US3 tasks: 7
- Suggested MVP scope: Phase 1 + Phase 2 + User Story 1
- All tasks include checkbox format, task IDs, story labels for story phases, and concrete file paths
- Stop at each story checkpoint to validate independent behavior before moving on
