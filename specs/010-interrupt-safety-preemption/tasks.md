# Tasks: Interrupt Safety and TTS Preemption

**Input**: Design documents from `/specs/010-interrupt-safety-preemption/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are REQUIRED because this feature changes runtime
interruption, TTS playback behavior, critical prompt acknowledgement, latency
measurement, and other safety-critical recovery flows.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this belongs to (e.g. `US1`, `US2`, `US3`)
- Include exact file paths in descriptions

## Path Conventions

- **Current project layout**: `main.py`, `controllers/`, `core/`, `settings/`, `tts/`, `ui/`, `tests/`, `docs/`
- **Feature focus**: interrupt detection and recovery in `core/assistant_runtime.py`, playback preemption in `tts/tts_engine.py`, speech dispatch handoff in `settings/settings_manager.py`, structured outcomes in `core/command_models.py`, prompt surfaces in `core/critical_prompts.py`, weak-network degraded recovery, and interrupt validation under `tests/unit/`, `tests/integration/`, and `tests/smoke/`
- **Specification docs**: `specs/010-interrupt-safety-preemption/contracts/` and `specs/010-interrupt-safety-preemption/quickstart.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare shared fixtures, smoke entry points, and validation evidence placeholders for Phase 10 work.

- [X] T001 Add canonical Phase 10 interrupt vocabulary fixtures, multilingual interrupt utterance samples, and preemptible playback doubles in `tests/conftest.py`
- [X] T002 [P] Create Phase 10 unit and integration scaffolding in `tests/unit/test_runtime_interrupt_preemption.py`, `tests/unit/test_tts_engine_interruptions.py`, and `tests/integration/test_runtime_interruptions.py`
- [X] T003 [P] Create Phase 10 smoke scaffolding in `tests/smoke/test_interrupt_safety_quickstart.py` and extend `tests/smoke/test_wearable_readiness_quickstart.py`
- [X] T004 [P] Add Phase 10 validation evidence placeholders in `specs/010-interrupt-safety-preemption/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared interrupt vocabulary, playback-preemption boundary, and structured recovery contracts required by all user stories.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Add failing unit coverage for canonical bilingual interrupt detection, mid-playback preemption, and structured recovery payloads in `tests/unit/test_runtime_interrupt_preemption.py`, `tests/unit/test_tts_engine_interruptions.py`, and `tests/unit/test_runtime_contract.py`
- [X] T006 [P] Add failing integration coverage for runtime interrupt recovery, localization integrity, standby recovery, and weak-network degraded handling in `tests/integration/test_runtime_interruptions.py`, `tests/integration/test_runtime_prompt_localization.py`, and `tests/integration/test_runtime_modes.py`
- [X] T007 [P] Add failing latency-baseline coverage for interrupt measurements under the defined moderate-load profile in `tests/unit/test_release_latency_baselines.py` and `tests/integration/test_release_latency_pipeline.py`
- [X] T008 Define shared interrupt vocabulary and runtime detection helpers in `core/assistant_runtime.py` and `core/wake_word.py`
- [X] T009 [P] Extend speech-service and structured recovery models for preemptible playback and provider-stall degraded outcomes in `tts/tts_engine.py`, `core/speech/interfaces.py`, and `core/command_models.py`
- [X] T010 [P] Add approved interrupt acknowledgement and best-effort cancellation prompt handling in `core/critical_prompts.py` and keep `settings/settings_manager.py` limited to runtime speech dispatch handoff
- [X] T011 Add interrupt observability and latency-capture hooks in `core/assistant_runtime.py` and `core/release_metrics.py`

**Checkpoint**: Interrupt foundation ready; user story implementation can begin.

---

## Phase 3: User Story 1 - Stop Speech Immediately (Priority: P1) MVP

**Goal**: Ensure approved Arabic and English stop or cancel phrases can preempt active spoken output quickly and return the runtime to a safe stable state.

**Independent Test**: Start a long spoken response, interrupt it with approved Arabic and English variants, and verify speech stops before completion while the runtime returns to standby safely.

### Tests for User Story 1

> **NOTE: Write these tests FIRST and ensure they fail before implementation
> because this story changes constitution-protected runtime, speech, and safety
> behavior.**

- [X] T012 [P] [US1] Extend unit coverage for bilingual interrupt vocabulary, ignored noise, and playback interruption outcomes in `tests/unit/test_runtime_interrupt_preemption.py` and `tests/unit/test_tts_engine_interruptions.py`
- [X] T013 [P] [US1] Extend integration coverage for accepted stop or cancel recovery and safe standby return in `tests/integration/test_runtime_interruptions.py` and `tests/integration/test_runtime_modes.py`
- [X] T014 [P] [US1] Add smoke coverage for English and Arabic speech-preemption quickstart paths in `tests/smoke/test_interrupt_safety_quickstart.py` and `tests/smoke/test_wearable_readiness_quickstart.py`

### Implementation for User Story 1

- [X] T015 [US1] Expand interrupt phrase detection to approved Arabic and English global safety vocabulary in `core/assistant_runtime.py` and `core/wake_word.py`
- [X] T016 [US1] Replace blocking playback behavior with genuinely preemptible speech stopping in `tts/tts_engine.py` and keep `settings/settings_manager.py` as dispatch plumbing only
- [X] T017 [US1] Preserve localized interrupt acknowledgement surfaces and prompt-integrity behavior in `core/critical_prompts.py` and `core/assistant_runtime.py`
- [X] T018 [US1] Emit structured accepted and ignored interrupt outcome fields, including standby recovery metadata, in `core/assistant_runtime.py` and `core/command_models.py`
- [X] T019 [US1] Run US1 validation (`python -m pytest tests/unit/test_runtime_interrupt_preemption.py tests/unit/test_tts_engine_interruptions.py tests/integration/test_runtime_interruptions.py tests/integration/test_runtime_modes.py tests/smoke/test_interrupt_safety_quickstart.py tests/smoke/test_wearable_readiness_quickstart.py -q`) and record SC-001, SC-002, and SC-003 evidence in `specs/010-interrupt-safety-preemption/quickstart.md`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Cancel In-Flight Work Safely (Priority: P2)

**Goal**: Ensure accepted interrupts suppress or cancel in-flight assistant work safely, including truthful best-effort handling for non-reversible operations.

**Independent Test**: Start a command or capability flow with spoken output and active work, interrupt it during thinking or speaking, and verify the assistant cancels safe work or reports a best-effort interruption without follow-on speech.

### Tests for User Story 2

- [X] T020 [P] [US2] Extend unit coverage for in-flight cancellation state, follow-on suppression, and best-effort interrupt outcomes in `tests/unit/test_assistant_runtime.py` and `tests/unit/test_runtime_interrupt_preemption.py`
- [X] T021 [P] [US2] Add integration coverage for interrupting speaking and thinking flows plus truthful best-effort and weak-network degraded outcomes in `tests/integration/test_runtime_interruptions.py` and `tests/integration/test_capability_runtime.py`
- [X] T022 [P] [US2] Extend smoke coverage for interrupting active work and suppressing follow-on speech in `tests/smoke/test_interrupt_safety_quickstart.py` and `tests/smoke/test_runtime_quickstart.py`

### Implementation for User Story 2

- [X] T023 [US2] Add in-flight operation tracking, cancellation-state handling, and follow-on suppression in `core/assistant_runtime.py` and `core/command_models.py`
- [X] T024 [US2] Propagate accepted interrupts through runtime-owned active operation handling in `core/assistant_runtime.py` while keeping `settings/settings_manager.py` as speech dispatch handoff only
- [X] T025 [US2] Implement truthful best-effort cancellation acknowledgement for non-reversible operations in `core/assistant_runtime.py` and `core/critical_prompts.py`
- [X] T026 [US2] Keep post-interrupt recovery deterministic by defaulting accepted interrupt flows back to safe standby in `core/assistant_runtime.py` and `tests/integration/test_runtime_interruptions.py`
- [X] T027 [US2] Run US2 validation (`python -m pytest tests/unit/test_assistant_runtime.py tests/unit/test_runtime_interrupt_preemption.py tests/integration/test_runtime_interruptions.py tests/integration/test_capability_runtime.py tests/smoke/test_interrupt_safety_quickstart.py tests/smoke/test_runtime_quickstart.py -q`) and record SC-003 evidence in `specs/010-interrupt-safety-preemption/quickstart.md`

**Checkpoint**: User Stories 1 and 2 are independently functional and testable.

---

## Phase 5: User Story 3 - Measurable Interrupt Reliability (Priority: P3)

**Goal**: Provide deterministic regression protection and measurable latency evidence for interrupt safety across normal and moderate-load validation paths.

**Independent Test**: Run the interrupt-focused regression suite, confirm structured recovery and latency metrics are emitted for accepted interrupts, and verify the measured latency stays within the Phase 10 target.

### Tests for User Story 3

- [X] T028 [P] [US3] Extend unit regression coverage for interrupt observability payloads and latency bucket classification in `tests/unit/test_runtime_contract.py` and `tests/unit/test_release_latency_baselines.py`
- [X] T029 [P] [US3] Extend integration coverage for interrupt latency reporting, the defined moderate-load profile, release-pipeline visibility, localization-backed acknowledgement, and weak-network degraded recovery in `tests/integration/test_runtime_interruptions.py`, `tests/integration/test_release_latency_pipeline.py`, and `tests/integration/test_runtime_prompt_localization.py`
- [X] T030 [P] [US3] Add smoke regression coverage for the full Phase 10 quickstart and latency guardrails in `tests/smoke/test_interrupt_safety_quickstart.py`

### Implementation for User Story 3

- [X] T031 [US3] Extend latency measurement and structured recovery emission for accepted interrupts in `core/release_metrics.py`, `core/assistant_runtime.py`, and `core/command_models.py`
- [X] T032 [US3] Update Phase 10 contracts and quickstart guidance to match shipped interrupt observability, canonical interrupt vocabulary, weak-network degraded behavior, and defined moderate-load latency behavior in `specs/010-interrupt-safety-preemption/contracts/interrupt-signal-contract.md`, `specs/010-interrupt-safety-preemption/contracts/preemption-outcome-contract.md`, and `specs/010-interrupt-safety-preemption/quickstart.md`
- [X] T033 [US3] Run US3 validation (`python -m pytest tests/unit/test_runtime_contract.py tests/unit/test_release_latency_baselines.py tests/integration/test_runtime_interruptions.py tests/integration/test_release_latency_pipeline.py tests/integration/test_runtime_prompt_localization.py tests/smoke/test_interrupt_safety_quickstart.py -q`) and record SC-004 and SC-005 evidence in `specs/010-interrupt-safety-preemption/quickstart.md`

**Checkpoint**: All user stories are independently functional and testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup, localization integrity coverage, edge-case hardening, and full validation across all stories.

- [X] T034 [P] Refresh critical-prompt and localization-integrity regression coverage for interrupt acknowledgement surfaces in `tests/unit/test_settings_critical_prompt_catalog.py` and `tests/integration/test_runtime_prompt_localization.py`
- [X] T035 Remove stale English-only interrupt parsing and post-playback-only interruption branches in `core/assistant_runtime.py` and `tts/tts_engine.py`
- [X] T036 [P] Add edge-case regression coverage for repeated interrupts, cross-language safety phrases, near-end playback interruption, ignored noise under the defined moderate-load profile, and provider-stall degraded recovery in `tests/unit/test_runtime_interrupt_preemption.py`, `tests/integration/test_runtime_interruptions.py`, and `tests/smoke/test_interrupt_safety_quickstart.py`
- [X] T037 Run full validation sweep (`python -m pytest tests/unit/test_runtime_interrupt_preemption.py tests/unit/test_tts_engine_interruptions.py tests/unit/test_assistant_runtime.py tests/unit/test_runtime_contract.py tests/unit/test_release_latency_baselines.py tests/unit/test_settings_critical_prompt_catalog.py -q`, `python -m pytest tests/integration/test_runtime_interruptions.py tests/integration/test_runtime_modes.py tests/integration/test_capability_runtime.py tests/integration/test_runtime_prompt_localization.py tests/integration/test_release_latency_pipeline.py -q`, `python -m pytest tests/smoke/test_interrupt_safety_quickstart.py tests/smoke/test_runtime_quickstart.py tests/smoke/test_wearable_readiness_quickstart.py -q`, `python -m compileall core tests`) and record outputs in `specs/010-interrupt-safety-preemption/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories
- **User Stories (Phases 3-5)**: Depend on Foundational completion
- **Polish (Phase 6)**: Depends on completion of the user stories selected for release scope

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on other stories
- **US2 (P2)**: Starts after Foundational; builds on the shared interrupt and preemption boundary from US1 but remains independently testable
- **US3 (P3)**: Starts after Foundational; its full regression and documentation pass should run after US1 and US2 behavior is in place

### Within Each User Story

- Write the listed tests first and confirm they fail before implementation
- Land shared runtime or speech-service boundary updates before provider-specific or latency-polish work
- Run the listed validation command and record evidence in `specs/010-interrupt-safety-preemption/quickstart.md` before marking the story complete

### Parallel Opportunities

- `T002`, `T003`, and `T004` can run in parallel after `T001`
- `T006` and `T007` can run in parallel during Foundational work
- `T012`, `T013`, and `T014` can run in parallel for US1
- `T020`, `T021`, and `T022` can run in parallel for US2
- `T028`, `T029`, and `T030` can run in parallel for US3
- `T034` and `T036` can run in parallel during Polish

---

## Parallel Example: User Story 1

```bash
Task: "Extend unit coverage for bilingual interrupt vocabulary, ignored noise, and playback interruption outcomes in tests/unit/test_runtime_interrupt_preemption.py and tests/unit/test_tts_engine_interruptions.py"
Task: "Extend integration coverage for accepted stop/cancel recovery and safe standby return in tests/integration/test_runtime_interruptions.py and tests/integration/test_runtime_modes.py"
Task: "Add smoke coverage for English and Arabic speech-preemption quickstart paths in tests/smoke/test_interrupt_safety_quickstart.py and tests/smoke/test_wearable_readiness_quickstart.py"
```

## Parallel Example: User Story 2

```bash
Task: "Extend unit coverage for in-flight cancellation state, follow-on suppression, and best-effort interrupt outcomes in tests/unit/test_assistant_runtime.py and tests/unit/test_runtime_interrupt_preemption.py"
Task: "Add integration coverage for interrupting speaking and thinking flows plus truthful best-effort outcomes in tests/integration/test_runtime_interruptions.py and tests/integration/test_capability_runtime.py"
Task: "Extend smoke coverage for interrupting active work and suppressing follow-on speech in tests/smoke/test_interrupt_safety_quickstart.py and tests/smoke/test_runtime_quickstart.py"
```

## Parallel Example: User Story 3

```bash
Task: "Extend unit regression coverage for interrupt observability payloads and latency bucket classification in tests/unit/test_runtime_contract.py and tests/unit/test_release_latency_baselines.py"
Task: "Extend integration coverage for interrupt latency reporting, release-pipeline visibility, and localization-backed acknowledgement in tests/integration/test_runtime_interruptions.py, tests/integration/test_release_latency_pipeline.py, and tests/integration/test_runtime_prompt_localization.py"
Task: "Add smoke regression coverage for the full Phase 10 quickstart and latency guardrails in tests/smoke/test_interrupt_safety_quickstart.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate interrupting active speech in Arabic and English before widening scope

### Incremental Delivery

1. Setup + Foundational establish the interrupt vocabulary, preemptible playback boundary, structured recovery model, and latency hooks
2. Deliver US1 for immediate speech interruption using the canonical interrupt vocabulary and safe standby recovery
3. Deliver US2 for in-flight cancellation and truthful best-effort interrupt outcomes
4. Deliver US3 for deterministic interrupt observability, latency evidence, and release-facing regression protection
5. Finish with Phase 6 polish and the full validation sweep

### Parallel Team Strategy

1. Team aligns on Setup and Foundational together
2. After Phase 2:
   - Developer A: US1 multilingual interrupt detection and TTS preemption
   - Developer B: US2 in-flight cancellation and best-effort recovery semantics
   - Developer C: US3 latency observability, contracts, and validation evidence
3. Rejoin for cross-cutting cleanup and final validation

---

## Notes

- `[P]` tasks are parallel-safe only after their dependency prerequisites are complete
- Every user story includes explicit test tasks because this feature touches runtime safety, playback behavior, localization integrity, and release-facing latency evidence
- Keep interrupt acknowledgement routed through approved critical prompt surfaces rather than embedded one-off strings
- Phase 10 is intentionally limited to interrupt vocabulary, TTS preemption, in-flight cancellation semantics, and interrupt validation rather than broader command-model redesign

