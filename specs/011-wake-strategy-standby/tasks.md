# Tasks: Wake Strategy and Low-Power Standby

**Input**: Design documents from `/specs/011-wake-strategy-standby/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are REQUIRED because this feature changes runtime standby
behavior, provider wake-policy resolution, settings application, structured
runtime outcomes, and release-facing latency evidence.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this belongs to (e.g. `US1`, `US2`, `US3`)
- Include exact file paths in descriptions

## Path Conventions

- **Current project layout**: `main.py`, `controllers/`, `core/`, `settings/`, `tts/`, `ui/`, `tests/`, `docs/`
- **Feature focus**: standby execution in `core/assistant_runtime.py`, wake-policy selection in `core/speech/provider_resolver.py`, wake descriptors in `core/speech/interfaces.py`, wake-provider plumbing in `core/speech/provider_registry.py` and wake adapters, structured wake outcomes in `core/command_models.py`, persisted wake settings in `settings/`, and wake validation under `tests/unit/`, `tests/integration/`, and `tests/smoke/`
- **Specification docs**: `specs/011-wake-strategy-standby/contracts/` and `specs/011-wake-strategy-standby/quickstart.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare wake-policy fixtures, smoke entry points, and validation evidence placeholders for Phase 11 work.

- [X] T001 Add Phase 11 wake-policy fixtures, wake-source availability toggles, and standby-session test doubles in `tests/conftest.py`
- [X] T002 [P] Create Phase 11 unit scaffolding in `tests/unit/test_provider_resolver.py`, `tests/unit/test_assistant_runtime.py`, and `tests/unit/test_runtime_contract.py`
- [X] T003 [P] Create Phase 11 integration scaffolding in `tests/integration/test_runtime_modes.py`, `tests/integration/test_wearable_startup_readiness.py`, and `tests/integration/test_gui_runtime_bridge.py`
- [X] T004 [P] Create Phase 11 smoke scaffolding in `tests/smoke/test_wake_strategy_quickstart.py` and add validation evidence placeholders in `specs/011-wake-strategy-standby/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared wake-policy, standby-outcome, wake-adapter, and latency-measurement boundaries required by all user stories.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Add failing unit coverage for wake-mode selection, canonical wake vocabulary, production STT guardrails, degraded standby guidance suppression, and structured wake outcomes in `tests/unit/test_provider_resolver.py`, `tests/unit/test_assistant_runtime.py`, and `tests/unit/test_runtime_contract.py`
- [X] T006 [P] Add failing integration coverage for standby waiting behavior, wake acceptance or rejection, and headless parity in `tests/integration/test_runtime_modes.py` and `tests/integration/test_wearable_startup_readiness.py`
- [X] T007 [P] Add failing GUI bridge parity coverage for wake-policy behavior in `tests/integration/test_gui_runtime_bridge.py`
- [X] T008 [P] Add failing latency-baseline coverage for the 10-cycle light-load scenario in `tests/unit/test_release_latency_baselines.py` and `tests/integration/test_release_latency_pipeline.py`
- [X] T009 Define wake-policy selection, canonical wake vocabulary, and degraded-standby decision helpers in `core/speech/provider_resolver.py`, `core/speech/interfaces.py`, and `core/wake_word.py`
- [X] T010 [P] Add structured wake-policy and standby-outcome models in `core/command_models.py` and `core/assistant_runtime.py`
- [X] T011 [P] Extend wake-service availability and wait-boundary plumbing in `core/speech/provider_registry.py`, `core/speech/legacy_wake.py`, and `core/speech/speakkit_wake.py`
- [X] T012 [P] Extend wake-setting persistence and runtime snapshot plumbing in `settings/profile_store.py`, `settings/settings_manager.py`, and `settings/user_profile.json`
- [X] T013 Add wake observability and latency-capture hooks for standby, wake acceptance, wake rejection, and baseline measurements in `core/assistant_runtime.py` and `core/release_metrics.py`

**Checkpoint**: Wake-policy foundation ready; user story implementation can begin.

---

## Phase 3: User Story 1 - Wake Safely in Standby (Priority: P1) MVP

**Goal**: Ensure production-like standby wakes only from permitted keyword or hardware-trigger signals and no longer relies on always-on free-form STT while idle.

**Independent Test**: Put the assistant into standby with production-like wake policy settings, verify keyword and hardware-trigger wake work, confirm forbidden STT idle input is ignored, and confirm competing permitted signals only start one wake cycle.

### Tests for User Story 1

> **NOTE: Write these tests FIRST and ensure they fail before implementation
> because this story changes constitution-protected runtime, provider, and
> safety behavior.**

- [X] T014 [P] [US1] Extend unit coverage for permitted keyword or hardware wake, canonical wake vocabulary, and forbidden STT standby input in `tests/unit/test_assistant_runtime.py` and `tests/unit/test_provider_resolver.py`
- [X] T015 [P] [US1] Add integration coverage for production-like standby wake acceptance and first-valid-wins wake-cycle locking in `tests/integration/test_runtime_modes.py` and `tests/integration/test_wearable_startup_readiness.py`
- [X] T016 [P] [US1] Add GUI bridge parity coverage for production-like wake handling in `tests/integration/test_gui_runtime_bridge.py`
- [X] T017 [P] [US1] Add smoke coverage for the production-like wake quickstart path in `tests/smoke/test_wake_strategy_quickstart.py` and `tests/smoke/test_wearable_readiness_quickstart.py`

### Implementation for User Story 1

- [X] T018 [US1] Replace always-on free-form standby STT listening with permitted wake-source waiting behavior in `core/assistant_runtime.py`
- [X] T019 [US1] Resolve production wake mode from configured primary and fallback modes in `core/speech/provider_resolver.py` and apply it in `core/assistant_runtime.py`
- [X] T020 [US1] Enforce first-valid-wins wake arbitration and wake-cycle locking in `core/assistant_runtime.py` and `core/command_models.py`
- [X] T021 [US1] Run US1 validation (`python -m pytest tests/unit/test_provider_resolver.py tests/unit/test_assistant_runtime.py tests/integration/test_runtime_modes.py tests/integration/test_wearable_startup_readiness.py tests/integration/test_gui_runtime_bridge.py tests/smoke/test_wake_strategy_quickstart.py tests/smoke/test_wearable_readiness_quickstart.py -q`) and record SC-001 evidence in `specs/011-wake-strategy-standby/quickstart.md`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Use a Development Wake Fallback (Priority: P2)

**Goal**: Ensure STT-based wake remains available only in explicitly allowed development scenarios and that unavailable or weak-network wake paths degrade safely with one-time guidance.

**Independent Test**: Run one development-allowed STT wake scenario and one production-like scenario, verify STT wake succeeds only in the development case, and verify unavailable or weak-network wake sources keep the assistant in safe degraded standby with bounded guidance.

### Tests for User Story 2

- [X] T022 [P] [US2] Extend unit coverage for development-only STT fallback selection, unavailable wake-source degraded standby, weak-network degraded standby, and one-time degraded guidance suppression in `tests/unit/test_provider_resolver.py`, `tests/unit/test_assistant_runtime.py`, and `tests/unit/test_settings_provider_persistence.py`
- [X] T023 [P] [US2] Add integration coverage for development STT wake, production STT rejection, and unavailable wake-source recovery in `tests/integration/test_runtime_modes.py`, `tests/integration/test_wearable_startup_readiness.py`, and `tests/integration/test_runtime_prompt_localization.py`
- [X] T024 [P] [US2] Add weak-network degraded standby coverage for provider-backed wake paths in `tests/integration/test_runtime_modes.py` and `tests/integration/test_runtime_offline_behavior.py`
- [X] T025 [P] [US2] Add smoke coverage for development fallback and degraded standby quickstart paths in `tests/smoke/test_wake_strategy_quickstart.py` and `tests/smoke/test_runtime_quickstart.py`

### Implementation for User Story 2

- [X] T026 [US2] Enforce dev-only STT fallback selection and production guardrails in `core/speech/provider_resolver.py` and `core/assistant_runtime.py`
- [X] T027 [US2] Persist and expose wake-policy settings consistently across runtime startup and test setup in `settings/profile_store.py`, `settings/settings_manager.py`, and `settings/user_profile.json`
- [X] T028 [US2] Emit one-time degraded standby guidance and reset it only on recovery or reason change in `core/assistant_runtime.py` and `core/critical_prompts.py`
- [X] T029 [US2] Record accepted or rejected wake attempts plus degraded standby outcomes in `core/assistant_runtime.py` and `core/command_models.py`
- [X] T030 [US2] Preserve local wake behavior during weak-network degraded standby when the selected wake source remains available in `core/assistant_runtime.py` and `core/speech/provider_resolver.py`
- [X] T031 [US2] Run US2 validation (`python -m pytest tests/unit/test_provider_resolver.py tests/unit/test_assistant_runtime.py tests/unit/test_settings_provider_persistence.py tests/integration/test_runtime_modes.py tests/integration/test_wearable_startup_readiness.py tests/integration/test_runtime_prompt_localization.py tests/integration/test_runtime_offline_behavior.py tests/smoke/test_wake_strategy_quickstart.py tests/smoke/test_runtime_quickstart.py -q`) and record SC-004, SC-004a, and SC-004b evidence in `specs/011-wake-strategy-standby/quickstart.md`

**Checkpoint**: User Stories 1 and 2 are independently functional and testable.

---

## Phase 5: User Story 3 - Measure Wake Readiness (Priority: P3)

**Goal**: Provide repeatable regression protection and measurable wake latency evidence for production-like and degraded standby paths.

**Independent Test**: Run the 10-cycle light-load wake baseline and the release smoke suite, then verify structured wake outcomes, latency records, and headless or GUI parity evidence are all emitted and reviewable.

### Tests for User Story 3

- [X] T032 [P] [US3] Extend unit coverage for wake outcome payloads, baseline buckets, and 10-cycle wake metrics in `tests/unit/test_runtime_contract.py` and `tests/unit/test_release_latency_baselines.py`
- [X] T033 [P] [US3] Add integration coverage for wake latency reporting and release-pipeline visibility in `tests/integration/test_release_latency_pipeline.py`, `tests/integration/test_runtime_modes.py`, and `tests/integration/test_release_journey_validation.py`
- [X] T034 [P] [US3] Add smoke coverage for headless wake parity and baseline capture in `tests/smoke/test_wake_strategy_quickstart.py`

### Implementation for User Story 3

- [X] T035 [US3] Extend wake-to-listen and listen-to-response baseline capture for the 10-cycle light-load scenario in `core/release_metrics.py` and `core/assistant_runtime.py`
- [X] T036 [US3] Align release-threshold and wake-journey consumption with the new baseline evidence in `settings/release_thresholds.json` and `core/release_journey_checks.py`
- [X] T037 [US3] Update Phase 11 contracts and quickstart guidance to match shipped canonical wake vocabulary, weak-network degraded behavior, GUI parity coverage, wake selection, standby outcome payloads, and baseline evidence in `specs/011-wake-strategy-standby/contracts/wake-mode-selection-contract.md`, `specs/011-wake-strategy-standby/contracts/standby-wake-outcome-contract.md`, and `specs/011-wake-strategy-standby/quickstart.md`
- [X] T038 [US3] Run US3 validation (`python -m pytest tests/unit/test_runtime_contract.py tests/unit/test_release_latency_baselines.py tests/integration/test_release_latency_pipeline.py tests/integration/test_runtime_modes.py tests/integration/test_release_journey_validation.py tests/smoke/test_wake_strategy_quickstart.py -q`) and record SC-002, SC-003, and SC-005 evidence in `specs/011-wake-strategy-standby/quickstart.md`

**Checkpoint**: All user stories are independently functional and testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup, localization integrity coverage, edge-case hardening, and full validation across all stories.

- [X] T039 [P] Refresh wake-guidance prompt and localization regression coverage in `tests/unit/test_settings_critical_prompt_catalog.py` and `tests/integration/test_runtime_prompt_localization.py`
- [X] T040 Remove stale standby STT fallback shortcuts and unused wake-selection branches in `core/assistant_runtime.py` and `core/speech/provider_resolver.py`
- [X] T041 [P] Add edge-case regression coverage for ambient speech false wakes, repeated degraded standby sessions, wake-source recovery, weak-network degraded wake behavior, and mixed-source races in `tests/unit/test_assistant_runtime.py`, `tests/integration/test_runtime_modes.py`, `tests/integration/test_runtime_offline_behavior.py`, and `tests/smoke/test_wake_strategy_quickstart.py`
- [X] T042 Run full validation sweep (`python -m pytest tests/unit/test_provider_resolver.py tests/unit/test_assistant_runtime.py tests/unit/test_runtime_contract.py tests/unit/test_release_latency_baselines.py tests/unit/test_settings_provider_persistence.py tests/unit/test_settings_critical_prompt_catalog.py -q`, `python -m pytest tests/integration/test_runtime_modes.py tests/integration/test_wearable_startup_readiness.py tests/integration/test_gui_runtime_bridge.py tests/integration/test_runtime_prompt_localization.py tests/integration/test_runtime_offline_behavior.py tests/integration/test_release_latency_pipeline.py tests/integration/test_release_journey_validation.py -q`, `python -m pytest tests/smoke/test_wake_strategy_quickstart.py tests/smoke/test_runtime_quickstart.py tests/smoke/test_wearable_readiness_quickstart.py -q`, `python -m compileall core tests`) and record outputs in `specs/011-wake-strategy-standby/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories
- **User Stories (Phases 3-5)**: Depend on Foundational completion
- **Polish (Phase 6)**: Depends on completion of the user stories selected for release scope

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on other stories
- **US2 (P2)**: Starts after Foundational; builds on the shared wake-policy boundary from US1 but remains independently testable
- **US3 (P3)**: Starts after Foundational; its full regression and baseline-evidence pass should run after US1 and US2 behavior is in place

### Within Each User Story

- Write the listed tests first and confirm they fail before implementation
- Land shared wake-policy or runtime-outcome boundary updates before story-specific smoke validation
- Run the listed validation command and record evidence in `specs/011-wake-strategy-standby/quickstart.md` before marking the story complete

### Parallel Opportunities

- `T002`, `T003`, and `T004` can run in parallel after `T001`
- `T006`, `T007`, `T008`, `T010`, `T011`, and `T012` can run in parallel during Foundational work
- `T014`, `T015`, `T016`, and `T017` can run in parallel for US1
- `T022`, `T023`, `T024`, and `T025` can run in parallel for US2
- `T032`, `T033`, and `T034` can run in parallel for US3
- `T039` and `T041` can run in parallel during Polish

---

## Parallel Example: User Story 1

```bash
Task: "Extend unit coverage for permitted keyword/hardware wake, canonical wake vocabulary, and forbidden STT standby input in tests/unit/test_assistant_runtime.py and tests/unit/test_provider_resolver.py"
Task: "Add integration coverage for production-like standby wake acceptance and first-valid-wins wake-cycle locking in tests/integration/test_runtime_modes.py and tests/integration/test_wearable_startup_readiness.py"
Task: "Add GUI bridge parity coverage for production-like wake handling in tests/integration/test_gui_runtime_bridge.py"
Task: "Add smoke coverage for the production-like wake quickstart path in tests/smoke/test_wake_strategy_quickstart.py and tests/smoke/test_wearable_readiness_quickstart.py"
```

## Parallel Example: User Story 2

```bash
Task: "Extend unit coverage for development-only STT fallback selection, unavailable wake-source degraded standby, weak-network degraded standby, and one-time degraded guidance suppression in tests/unit/test_provider_resolver.py, tests/unit/test_assistant_runtime.py, and tests/unit/test_settings_provider_persistence.py"
Task: "Add integration coverage for development STT wake, production STT rejection, and unavailable wake-source recovery in tests/integration/test_runtime_modes.py, tests/integration/test_wearable_startup_readiness.py, and tests/integration/test_runtime_prompt_localization.py"
Task: "Add weak-network degraded standby coverage for provider-backed wake paths in tests/integration/test_runtime_modes.py and tests/integration/test_runtime_offline_behavior.py"
Task: "Add smoke coverage for development fallback and degraded standby quickstart paths in tests/smoke/test_wake_strategy_quickstart.py and tests/smoke/test_runtime_quickstart.py"
```

## Parallel Example: User Story 3

```bash
Task: "Extend unit coverage for wake outcome payloads, baseline buckets, and 10-cycle wake metrics in tests/unit/test_runtime_contract.py and tests/unit/test_release_latency_baselines.py"
Task: "Add integration coverage for wake latency reporting and release-pipeline visibility in tests/integration/test_release_latency_pipeline.py, tests/integration/test_runtime_modes.py, and tests/integration/test_release_journey_validation.py"
Task: "Add smoke coverage for headless wake parity and baseline capture in tests/smoke/test_wake_strategy_quickstart.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate production-like keyword or hardware standby wake before widening scope

### Incremental Delivery

1. Setup + Foundational establish wake-policy selection, canonical wake vocabulary, wake-adapter plumbing, standby outcome models, settings plumbing, and baseline hooks
2. Deliver US1 for production-safe low-power standby and first-valid-wins wake arbitration
3. Deliver US2 for development-only STT fallback, weak-network degraded truthfulness, and bounded degraded standby guidance
4. Deliver US3 for measurable wake baselines and release-facing regression evidence
5. Finish with Phase 6 polish and the full validation sweep

### Parallel Team Strategy

1. Team aligns on Setup and Foundational together
2. After Phase 2:
   - Developer A: US1 standby waiting behavior and wake arbitration
   - Developer B: US2 dev fallback, degraded standby guidance, and settings persistence
   - Developer C: US3 wake latency baselines, release thresholds, and validation evidence
3. Rejoin for cross-cutting cleanup and final validation

---

## Notes

- `[P]` tasks are parallel-safe only after their dependency prerequisites are complete
- Every user story includes explicit test tasks because this feature touches runtime safety, provider policy, settings application, and release-facing latency evidence
- Keep wake-policy decisions runtime-owned; persisted settings stay in `settings/`, but feature workflow logic must remain in `core/`
- Phase 11 is intentionally limited to wake-policy enforcement, low-power standby behavior, degraded standby safety, and wake-readiness validation rather than broader command or capability changes
