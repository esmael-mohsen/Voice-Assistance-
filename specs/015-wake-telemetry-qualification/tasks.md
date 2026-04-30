# Tasks: Wake Reliability, Telemetry, and Raspberry Pi Performance Qualification

**Input**: Design documents from `/specs/015-wake-telemetry-qualification/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are REQUIRED because this feature changes wake behavior,
runtime orchestration, prompt playback policy, provider fallback behavior,
structured telemetry, and release-facing Raspberry Pi qualification gates.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this belongs to (e.g. `US1`, `US2`, `US3`)
- Include exact file paths in descriptions

## Path Conventions

- **Current project layout**: `main.py`, `controllers/`, `core/`, `settings/`, `tts/`, `ui/`, `tests/`, `docs/`, `scripts/`
- **Feature focus**: wake evaluation in `core/wake_word.py` and `core/speech/*wake.py`; speech-loop orchestration in `core/assistant_runtime.py` and `core/stt.py`; prompt playback policy in `tts/tts_engine.py`; telemetry, qualification, and release gating in `core/runtime_diagnostics.py`, `core/release_metrics.py`, `core/release_models.py`, and `core/release_gates.py`; operator guidance in `docs/release/startup.md` and `docs/release/troubleshooting.md`
- **Specification docs**: `specs/015-wake-telemetry-qualification/contracts/` and `specs/015-wake-telemetry-qualification/quickstart.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare replay fixtures, qualification evidence placeholders, and test entry points for Phase 15.

- [X] T001 Add Phase 15 replay-scenario fixtures, wake-alias catalogs, and local artifact-bundle helpers in `tests/conftest.py` and `tests/fixtures/wake/README.md`
- [X] T002 [P] Create Phase 15 unit-test scaffolding in `tests/unit/test_wake_word_profiles.py`, `tests/unit/test_wake_strategy_runtime.py`, `tests/unit/test_tts_engine_interruptions.py`, `tests/unit/test_runtime_contract.py`, and `tests/unit/test_release_gate_models.py`
- [X] T003 [P] Create Phase 15 integration-test scaffolding in `tests/integration/test_wake_strategy_modes.py`, `tests/integration/test_runtime_modes.py`, `tests/integration/test_speech_telemetry_pipeline.py`, and `tests/integration/test_pi_qualification_release_gates.py`
- [X] T004 [P] Create Phase 15 smoke scaffolding and evidence placeholders in `tests/smoke/test_wake_strategy_quickstart.py`, `tests/smoke/test_runtime_quickstart.py`, `tests/smoke/test_speech_provider_quickstart.py`, `docs/release/startup.md`, `docs/release/troubleshooting.md`, and `specs/015-wake-telemetry-qualification/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared wake-policy, recovery, telemetry, and qualification boundaries required by all user stories.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Add failing unit coverage for wake policy profiles, weak-detection confirmation decisions, structured wake outcomes, and release-gate model rules in `tests/unit/test_wake_word_profiles.py`, `tests/unit/test_runtime_contract.py`, and `tests/unit/test_release_gate_models.py`
- [X] T006 [P] Add failing unit coverage for prompt-class barge-in, protected-prompt blocking, and three-fault speech-loop reset behavior in `tests/unit/test_wake_strategy_runtime.py`, `tests/unit/test_tts_engine_interruptions.py`, and `tests/unit/test_assistant_runtime.py`
- [X] T007 [P] Add failing integration coverage for confirmation-window wake handling, multilingual wake aliases, and production-vs-development wake separation in `tests/integration/test_wake_strategy_modes.py`, `tests/integration/test_runtime_modes.py`, and `tests/integration/test_wearable_startup_readiness.py`
- [X] T008 [P] Add failing integration coverage for telemetry sink failure resilience, replay scenario evidence capture, and Pi-missing release-gate blocking in `tests/integration/test_speech_telemetry_pipeline.py`, `tests/integration/test_pi_qualification_release_gates.py`, and `tests/integration/test_release_gate_pipeline.py`
- [X] T009 [P] Add failing smoke coverage for headless wake-to-listen behavior, degraded recovery, and release-gate quickstart validation in `tests/smoke/test_wake_strategy_quickstart.py`, `tests/smoke/test_runtime_quickstart.py`, and `tests/smoke/test_speech_provider_quickstart.py`
- [X] T010 Define structured wake-reliability and speech-loop-recovery result models in `core/command_models.py`
- [X] T011 [P] Implement shared wake scoring, canonical alias grouping, and confirmation-window helpers in `core/wake_word.py` and `core/speech/legacy_wake.py`
- [X] T012 [P] Extend wake-provider interfaces, resolver policy inputs, future hardware-trigger compatibility, and adapter metadata plumbing in `core/speech/interfaces.py`, `core/speech/provider_resolver.py`, and `core/speech/speakkit_wake.py`
- [X] T013 [P] Add wake-policy, confirmation-window, and qualification-setting persistence fields in `settings/profile_store.py`, `settings/settings_manager.py`, and `settings/user_profile.json`
- [X] T014 [P] Add shared telemetry event persistence and local artifact routing helpers in `core/runtime_diagnostics.py` and `core/release_metrics.py`
- [X] T015 [P] Add Pi qualification and speech release-gate data structures plus evaluation plumbing in `core/release_models.py` and `core/release_gates.py`

**Checkpoint**: Shared wake, telemetry, settings, and release-gate boundaries are ready; user story work can begin.

---

## Phase 3: User Story 1 - Wake Cleanly Into Listening (Priority: P1) MVP

**Goal**: Let the assistant wake quickly from low-cost standby, accept clear wakes directly, and use only one bounded confirmation step for weak or noisy detections.

**Independent Test**: Run quiet, noisy, and bilingual wake trials in headless mode, then confirm clear supported wakes move straight to listening, weak detections use one confirmation window, and production mode never silently uses dev-only wake behavior.

### Tests for User Story 1

> **NOTE: Write these tests FIRST and ensure they fail before implementation
> because this story changes constitution-protected wake, provider, runtime,
> and headless interaction behavior.**

- [X] T016 [P] [US1] Extend unit coverage for acceptance thresholds, weak-detection confirmation, and canonical wake alias handling in `tests/unit/test_wake_word_profiles.py` and `tests/unit/test_wake_word_canonical.py`
- [X] T017 [P] [US1] Add integration coverage for direct-listen acceptance, bounded confirmation-window behavior, and production wake guardrails in `tests/integration/test_wake_strategy_modes.py`, `tests/integration/test_runtime_modes.py`, and `tests/integration/test_wearable_startup_readiness.py`
- [X] T018 [P] [US1] Add smoke coverage for quiet, noisy, and bilingual wake quickstart journeys in `tests/smoke/test_wake_strategy_quickstart.py` and `tests/smoke/test_runtime_quickstart.py`

### Implementation for User Story 1

- [X] T019 [US1] Implement tiered wake scoring, canonical alias normalization, and bounded confirmation-window transitions in `core/wake_word.py` and `core/speech/legacy_wake.py`
- [X] T020 [US1] Apply production wake selection and explicit development-fallback separation during standby entry in `core/assistant_runtime.py` and `core/speech/provider_resolver.py`
- [X] T021 [US1] Surface weak-detection and confirmation metadata from concrete wake adapters in `core/speech/legacy_wake.py`, `core/speech/speakkit_wake.py`, and `core/speech/interfaces.py`
- [X] T022 [US1] Emit structured wake outcomes, false-accept or false-reject review flags, and wake-to-listen telemetry for accepted, rejected, and confirmed wakes in `core/assistant_runtime.py`, `core/command_models.py`, and `core/runtime_diagnostics.py`
- [X] T023 [US1] Run US1 validation (`python -m pytest tests/unit/test_wake_word_profiles.py tests/unit/test_wake_word_canonical.py tests/integration/test_wake_strategy_modes.py tests/integration/test_runtime_modes.py tests/integration/test_wearable_startup_readiness.py tests/smoke/test_wake_strategy_quickstart.py tests/smoke/test_runtime_quickstart.py -q`) and record `SC-001` evidence in `specs/015-wake-telemetry-qualification/quickstart.md` and `docs/release/startup.md`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Recover Safely During Speech Failures (Priority: P2)

**Goal**: Coordinate wake, listening, and prompt playback safely so ordinary wake or speech faults return the assistant to standby or a truthful supported mode instead of stalling or exiting.

**Independent Test**: Exercise wake misses, prompt interruption, provider timeouts, and degraded-mode flows, then confirm safe barge-in works only on allowed prompts, protected prompts remain guarded, and the assistant resets to standby after three consecutive ordinary faults.

### Tests for User Story 2

- [X] T024 [P] [US2] Extend unit coverage for prompt-class barge-in, protected prompt blocking, and three-fault reset behavior in `tests/unit/test_tts_engine_interruptions.py`, `tests/unit/test_wake_strategy_runtime.py`, and `tests/unit/test_assistant_runtime.py`
- [X] T025 [P] [US2] Add integration coverage for wake/listen/playback turn-taking, provider timeout recovery, and degraded truthfulness in `tests/integration/test_runtime_modes.py`, `tests/integration/test_runtime_offline_behavior.py`, and `tests/integration/test_gui_runtime_bridge.py`
- [X] T026 [P] [US2] Add smoke coverage for degraded recovery, protected prompts, and standby-reset quickstart paths in `tests/smoke/test_runtime_quickstart.py` and `tests/smoke/test_speech_provider_quickstart.py`

### Implementation for User Story 2

- [X] T027 [US2] Classify spoken prompts and enforce safe barge-in boundaries in `tts/tts_engine.py`, `core/critical_prompts.py`, and `core/assistant_runtime.py`
- [X] T028 [US2] Implement the shared three-fault recovery budget and standby reset path in `core/assistant_runtime.py` and `core/stt.py`
- [X] T029 [US2] Preserve truthful degraded-mode speech and telemetry-sink-failure resilience in `core/assistant_runtime.py`, `core/runtime_diagnostics.py`, and `core/speech/provider_resolver.py`
- [X] T030 [US2] Emit structured recovery outcomes plus clarification-loop, prompt-echo, clipped-utterance retry, and command-confidence telemetry in `core/command_models.py`, `core/release_metrics.py`, and `core/runtime_diagnostics.py`
- [X] T031 [US2] Run US2 validation (`python -m pytest tests/unit/test_tts_engine_interruptions.py tests/unit/test_wake_strategy_runtime.py tests/unit/test_assistant_runtime.py tests/integration/test_runtime_modes.py tests/integration/test_runtime_offline_behavior.py tests/integration/test_gui_runtime_bridge.py tests/smoke/test_runtime_quickstart.py tests/smoke/test_speech_provider_quickstart.py -q`) and record `SC-002` evidence in `specs/015-wake-telemetry-qualification/quickstart.md` and `docs/release/troubleshooting.md`

**Checkpoint**: User Stories 1 and 2 are independently functional and testable.

---

## Phase 5: User Story 3 - Qualify Releases on Raspberry Pi 4 (Priority: P3)

**Goal**: Produce lightweight speech telemetry, repeatable replay evidence, and real-hardware Raspberry Pi 4 qualification plus release-gate decisions for candidate builds.

**Independent Test**: Run replay scenarios and Raspberry Pi 4 qualification, then confirm telemetry is written to local artifacts, CI replay and Pi evidence are evaluated separately, and candidate builds are blocked when required hardware evidence or resource budgets fail.

### Tests for User Story 3

- [X] T032 [P] [US3] Extend unit coverage for telemetry event shaping, Pi qualification records, and speech release-gate rules in `tests/unit/test_release_gate_models.py`, `tests/unit/test_runtime_contract.py`, and `tests/unit/test_release_latency_baselines.py`
- [X] T033 [P] [US3] Add integration coverage for replay telemetry collection, local artifact persistence, and CI-vs-Pi gate decisions in `tests/integration/test_speech_telemetry_pipeline.py`, `tests/integration/test_pi_qualification_release_gates.py`, and `tests/integration/test_release_gate_pipeline.py`
- [X] T034 [P] [US3] Add smoke coverage for replay evidence review and release-gate quickstart validation in `tests/smoke/test_wake_strategy_quickstart.py` and `tests/smoke/test_speech_provider_quickstart.py`

### Implementation for User Story 3

- [X] T035 [US3] Implement lightweight speech telemetry emission, command-confidence summaries, and local candidate-artifact persistence in `core/runtime_diagnostics.py`, `core/release_metrics.py`, and `core/assistant_runtime.py`
- [X] T036 [US3] Implement replay-scenario execution, evidence completeness checks, and telemetry validation in `core/release_journey_checks.py`, `core/release_metrics.py`, and `core/release_models.py`
- [X] T037 [US3] Implement Raspberry Pi 4 qualification summaries, threshold evaluation, and pilot-blocking release-gate rules in `core/release_gates.py`, `core/release_models.py`, and `settings/release_thresholds.json`
- [X] T038 [US3] Update operator guidance and candidate-evidence review instructions in `docs/release/startup.md`, `docs/release/troubleshooting.md`, and `specs/015-wake-telemetry-qualification/quickstart.md`
- [ ] T039 [US3] Run US3 validation (`python -m pytest tests/unit/test_release_gate_models.py tests/unit/test_runtime_contract.py tests/unit/test_release_latency_baselines.py tests/integration/test_speech_telemetry_pipeline.py tests/integration/test_pi_qualification_release_gates.py tests/integration/test_release_gate_pipeline.py tests/smoke/test_wake_strategy_quickstart.py tests/smoke/test_speech_provider_quickstart.py -q` plus the Phase 15 Raspberry Pi 4 qualification run) and record `SC-003` and `SC-004` evidence in `specs/015-wake-telemetry-qualification/quickstart.md`, `docs/release/startup.md`, and `docs/release/troubleshooting.md`

**Checkpoint**: All user stories are independently functional and qualification-ready.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final contract alignment, regression hardening, and full feature verification across all stories.

- [X] T040 [P] Refresh Phase 15 contracts to match shipped wake, telemetry, recovery, qualification, and release-gate payloads in `specs/015-wake-telemetry-qualification/contracts/wake-reliability-outcome-contract.md`, `specs/015-wake-telemetry-qualification/contracts/speech-telemetry-event-contract.md`, `specs/015-wake-telemetry-qualification/contracts/speech-loop-recovery-contract.md`, `specs/015-wake-telemetry-qualification/contracts/pi-qualification-run-contract.md`, and `specs/015-wake-telemetry-qualification/contracts/speech-release-gate-contract.md`
- [X] T041 Remove stale wake shortcuts, unguarded prompt-interruption paths, and fallback logic that bypasses Phase 15 guardrails in `core/assistant_runtime.py`, `core/wake_word.py`, `tts/tts_engine.py`, and `core/speech/provider_resolver.py`
- [X] T042 [P] Add regression coverage for false-accept review flags, telemetry sink failures, replay artifact gaps, and Pi-missing release blocks in `tests/unit/test_release_gate_models.py`, `tests/integration/test_speech_telemetry_pipeline.py`, `tests/integration/test_release_gate_pipeline.py`, and `tests/smoke/test_speech_provider_quickstart.py`
- [X] T043 Run the full validation sweep from `specs/015-wake-telemetry-qualification/quickstart.md` (`python -m pytest tests/unit/test_wake_word_profiles.py tests/unit/test_wake_word_canonical.py tests/unit/test_wake_strategy_runtime.py tests/unit/test_tts_engine_interruptions.py tests/unit/test_runtime_contract.py tests/unit/test_release_gate_models.py tests/unit/test_assistant_runtime.py tests/unit/test_release_latency_baselines.py -q`; `python -m pytest tests/integration/test_wake_strategy_modes.py tests/integration/test_runtime_modes.py tests/integration/test_wearable_startup_readiness.py tests/integration/test_runtime_offline_behavior.py tests/integration/test_gui_runtime_bridge.py tests/integration/test_speech_telemetry_pipeline.py tests/integration/test_pi_qualification_release_gates.py tests/integration/test_release_gate_pipeline.py -q`; `python -m pytest tests/smoke/test_wake_strategy_quickstart.py tests/smoke/test_runtime_quickstart.py tests/smoke/test_speech_provider_quickstart.py -q`; `python -m compileall core tests`; `ruff check .`) and record outputs in `specs/015-wake-telemetry-qualification/quickstart.md`, `docs/release/startup.md`, and `docs/release/troubleshooting.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on the shared wake boundary from Foundational and builds on the runtime wake flow delivered by US1
- **User Story 3 (Phase 5)**: Depends on Foundational completion and should run after US1 and US2 behavior is in place so qualification measures the shipped wake and recovery path
- **Polish (Phase 6)**: Depends on completion of the user stories selected for release scope

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on other stories
- **US2 (P2)**: Builds on US1 wake transitions and adds turn-taking, recovery, and degraded-mode truthfulness
- **US3 (P3)**: Builds on US1 and US2 to qualify real shipped behavior and publish release-gate evidence

### Within Each User Story

- Write the listed tests first and confirm they fail before implementation
- Land the story's runtime and structured-result plumbing before recording quickstart evidence
- Run the listed validation command and update `specs/015-wake-telemetry-qualification/quickstart.md` before marking the story complete

### Parallel Opportunities

- `T002`, `T003`, and `T004` can run in parallel after `T001`
- `T006`, `T007`, `T008`, `T009`, `T011`, `T012`, `T013`, `T014`, and `T015` can run in parallel after `T005`
- `T016`, `T017`, and `T018` can run in parallel for US1
- `T024`, `T025`, and `T026` can run in parallel for US2
- `T032`, `T033`, and `T034` can run in parallel for US3
- `T040` and `T042` can run in parallel during Polish

---

## Parallel Example: User Story 1

```bash
Task: "Extend unit coverage for acceptance thresholds, weak-detection confirmation, and canonical wake alias handling in tests/unit/test_wake_word_profiles.py and tests/unit/test_wake_word_canonical.py"
Task: "Add integration coverage for direct-listen acceptance, bounded confirmation-window behavior, and production wake guardrails in tests/integration/test_wake_strategy_modes.py, tests/integration/test_runtime_modes.py, and tests/integration/test_wearable_startup_readiness.py"
Task: "Add smoke coverage for quiet, noisy, and bilingual wake quickstart journeys in tests/smoke/test_wake_strategy_quickstart.py and tests/smoke/test_runtime_quickstart.py"
```

## Parallel Example: User Story 2

```bash
Task: "Extend unit coverage for prompt-class barge-in, protected prompt blocking, and three-fault reset behavior in tests/unit/test_tts_engine_interruptions.py, tests/unit/test_wake_strategy_runtime.py, and tests/unit/test_assistant_runtime.py"
Task: "Add integration coverage for wake/listen/playback turn-taking, provider timeout recovery, and degraded truthfulness in tests/integration/test_runtime_modes.py, tests/integration/test_runtime_offline_behavior.py, and tests/integration/test_gui_runtime_bridge.py"
Task: "Add smoke coverage for degraded recovery, protected prompts, and standby-reset quickstart paths in tests/smoke/test_runtime_quickstart.py and tests/smoke/test_speech_provider_quickstart.py"
```

## Parallel Example: User Story 3

```bash
Task: "Extend unit coverage for telemetry event shaping, Pi qualification records, and speech release-gate rules in tests/unit/test_release_gate_models.py, tests/unit/test_runtime_contract.py, and tests/unit/test_release_latency_baselines.py"
Task: "Add integration coverage for replay telemetry collection, local artifact persistence, and CI-vs-Pi gate decisions in tests/integration/test_speech_telemetry_pipeline.py, tests/integration/test_pi_qualification_release_gates.py, and tests/integration/test_release_gate_pipeline.py"
Task: "Add smoke coverage for replay evidence review and release-gate quickstart validation in tests/smoke/test_wake_strategy_quickstart.py and tests/smoke/test_speech_provider_quickstart.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate wake acceptance, weak-detection confirmation, and production wake guardrails before widening scope

### Incremental Delivery

1. Setup + Foundational establish wake scoring, confirmation policy, structured results, telemetry persistence, and qualification boundaries
2. Deliver US1 for clean wake-to-listen behavior with bounded confirmation windows
3. Deliver US2 for safe barge-in, repeated-fault recovery, and degraded truthfulness
4. Deliver US3 for local telemetry evidence, Raspberry Pi 4 qualification, and release-gate enforcement
5. Finish with Phase 6 polish and the full validation sweep

### Parallel Team Strategy

1. Team aligns on Setup and Foundational together
2. After Phase 2:
   - Developer A: US1 wake scoring, alias handling, and confirmation-window flow
   - Developer B: US2 prompt policy, recovery budget, and degraded speech behavior
   - Developer C: US3 telemetry artifacts, Pi qualification, and release-gate rules
3. Rejoin for cross-cutting cleanup and full validation

---

## Notes

- `[P]` tasks are parallel-safe only after their prerequisite tasks are complete
- Every user story includes explicit test tasks because this feature touches wake safety, runtime orchestration, provider fallback behavior, telemetry, and release gating
- Keep runtime speech decisions in `core/` and `tts/`; GUI surfaces should observe the same behavior rather than define separate wake or recovery rules
- Local artifact evidence is the default telemetry path; optional external sinks must never become a hard dependency for live interaction or release qualification
