# Tasks: Continuous Turn-Taking, Closed-Vocabulary Guardrails, and Pilot-Grade Voice UX

**Input**: Design documents from `/specs/016-voice-ux-guardrails/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are REQUIRED because this feature changes runtime
orchestration, STT filtering, resolver safety behavior, prompt playback
coordination, settings-backed dialog policy, and pilot UX evidence generation.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this belongs to (e.g. `US1`, `US2`, `US3`)
- Include exact file paths in descriptions

## Path Conventions

- **Current project layout**: `main.py`, `controllers/`, `core/`, `settings/`, `tts/`, `ui/`, `tests/`, `docs/`, `scripts/`
- **Feature focus**: guided runtime flow in `core/assistant_runtime.py`; shared dialog helpers in `core/dialog_policy.py`; closed-choice capture and filtering in `core/stt.py`; protected-flow resolution in `core/resolver.py`; structured runtime results in `core/command_models.py`; prompt catalog surfaces in `core/critical_prompts.py`; new turn-taking and vocabulary modules in `core/turn_taking.py` and `core/closed_vocabulary.py`; persisted policy defaults in `settings/settings_manager.py`, `settings/profile_store.py`, and `settings/user_profile.json`; playback coordination in `tts/tts_engine.py`; pilot evidence helpers in `core/release_artifacts.py`, `core/release_metrics.py`, and `core/release_models.py`
- **Specification docs**: `specs/016-voice-ux-guardrails/contracts/` and `specs/016-voice-ux-guardrails/quickstart.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare guided-dialog fixtures, test entry points, and pilot evidence placeholders for Phase 16.

- [X] T001 Create Phase 16 guided-dialog fixture notes and artifact placeholder guidance in `tests/fixtures/dialog/README.md` and `specs/016-voice-ux-guardrails/quickstart.md`
- [X] T002 [P] Create Phase 16 unit-test scaffolding in `tests/unit/test_turn_taking.py`, `tests/unit/test_closed_vocabulary.py`, `tests/unit/test_dialog_confirmation_policy.py`, `tests/unit/test_assistant_runtime.py`, `tests/unit/test_runtime_contract.py`, `tests/unit/test_resolver.py`, and `tests/unit/test_tts_engine_interruptions.py`
- [X] T003 [P] Create Phase 16 integration-test scaffolding in `tests/integration/test_command_dialog_robustness.py`, `tests/integration/test_closed_vocabulary_stt.py`, `tests/integration/test_command_recognition_runtime.py`, `tests/integration/test_runtime_interruptions.py`, `tests/integration/test_runtime_failure_paths.py`, `tests/integration/test_gui_runtime_bridge.py`, and `tests/integration/test_release_journey_validation.py`
- [X] T004 [P] Create Phase 16 smoke and pilot-evidence scaffolding in `tests/smoke/test_runtime_quickstart.py`, `docs/release/checklist.md`, and `specs/016-voice-ux-guardrails/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared turn-taking, closed-vocabulary, prompt-catalog, and structured-result boundaries required by all user stories.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Add failing unit coverage for turn-taking window states, closed-vocabulary registry validation, and guided-dialog outcome contracts in `tests/unit/test_turn_taking.py`, `tests/unit/test_closed_vocabulary.py`, and `tests/unit/test_runtime_contract.py`
- [X] T006 [P] Add failing integration coverage for guided context preservation, prompt-echo suppression accounting, and field-safe pilot evidence shaping in `tests/integration/test_command_dialog_robustness.py`, `tests/integration/test_closed_vocabulary_stt.py`, and `tests/integration/test_runtime_failure_paths.py`
- [X] T007 [P] Add failing smoke coverage for early-answer, protected-prompt, and pilot-evidence quickstart flows in `tests/smoke/test_runtime_quickstart.py`
- [X] T008 Define structured turn-taking, guided-dialog, name-candidate, and pilot-evidence result models in `core/command_models.py`
- [X] T009 [P] Implement the shared turn-taking coordinator and prompt-class policy helpers in `core/turn_taking.py`
- [X] T010 [P] Implement the shared closed-vocabulary registry, option metadata, and fallback strategy helpers in `core/closed_vocabulary.py`
- [X] T011 [P] Extend critical prompt catalog surfaces and shorter retry wording for Phase 16 guided flows in `core/critical_prompts.py`
- [X] T012 [P] Add persisted dialog-policy defaults and retry settings alignment in `settings/profile_store.py`, `settings/settings_manager.py`, and `settings/user_profile.json`

**Checkpoint**: Shared guided-dialog contracts, registry, settings defaults, and prompt surfaces are ready; user story work can begin.

---

## Phase 3: User Story 1 - Answer Naturally During Guided Prompts (Priority: P1) MVP

**Goal**: Let users answer eligible onboarding and settings prompts naturally during playback while protected confirmations, shutdown, and destructive flows remain strict.

**Independent Test**: Run guided prompts for onboarding choices, low-risk settings, informational prompts, and retry/help turns where users answer before prompt completion, during allowed playback, and immediately after prompt completion, then confirm accepted turns are captured without repeat prompts and protected prompts block early input until safe.

### Tests for User Story 1

> **NOTE: Write these tests FIRST and ensure they fail before implementation**
> because this story changes constitution-protected runtime orchestration,
> prompt playback policy, and headless interaction behavior.

- [X] T013 [P] [US1] Extend unit coverage for eligible barge-in windows, protected prompt blocking, and prompt-class transitions in `tests/unit/test_turn_taking.py`, `tests/unit/test_assistant_runtime.py`, and `tests/unit/test_tts_engine_interruptions.py`
- [X] T014 [P] [US1] Add integration coverage for early answers during onboarding or settings playback and protected-flow interruption blocking in `tests/integration/test_command_recognition_runtime.py`, `tests/integration/test_runtime_interruptions.py`, and `tests/integration/test_gui_runtime_bridge.py`
- [X] T015 [P] [US1] Add smoke coverage for allowed early-answer and protected-prompt quickstart journeys in `tests/smoke/test_runtime_quickstart.py`

### Implementation for User Story 1

- [X] T016 [US1] Integrate `core/turn_taking.py` with guided prompt transitions and answer-window selection in `core/assistant_runtime.py`
- [X] T017 [US1] Add prompt-class metadata and barge-in safety boundaries for onboarding, info, retry, confirmation, shutdown, and destructive prompts in `core/critical_prompts.py` and `core/turn_taking.py`
- [X] T018 [US1] Coordinate prompt playback interruption and early-answer capture in `tts/tts_engine.py` and `core/assistant_runtime.py`
- [X] T019 [US1] Preserve strict protected-flow handling for confirmation, shutdown, and destructive turns in `core/resolver.py` and `core/assistant_runtime.py`
- [X] T020 [US1] Run US1 validation (`python -m pytest tests/unit/test_turn_taking.py tests/unit/test_assistant_runtime.py tests/unit/test_tts_engine_interruptions.py tests/integration/test_command_recognition_runtime.py tests/integration/test_runtime_interruptions.py tests/integration/test_gui_runtime_bridge.py tests/smoke/test_runtime_quickstart.py -q`) and record `SC-001` evidence in `specs/016-voice-ux-guardrails/quickstart.md`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Keep Closed-Choice Dialogs On Track (Priority: P2)

**Goal**: Resolve closed-choice prompts through a bilingual registry that accepts supported aliases, rejects out-of-domain speech safely, suppresses prompt echo, and keeps unrelated non-safety commands inside the guided context.

**Independent Test**: Exercise each closed-vocabulary context with valid aliases, mixed-language variants, near misses, unrelated answers, and non-safety commands, then confirm only approved answers resolve the dialog, only approved global safety commands may preempt, prompt echo is suppressed without burning retry budget, and all other inputs trigger bounded recovery.

### Tests for User Story 2

- [X] T021 [P] [US2] Extend unit coverage for bilingual alias matching, closed-vocabulary retry limits, and prompt-echo suppression rules in `tests/unit/test_closed_vocabulary.py`, `tests/unit/test_dialog_confirmation_policy.py`, and `tests/unit/test_assistant_runtime.py`
- [X] T022 [P] [US2] Add integration coverage for closed-vocabulary STT filtering, guided-context preservation, out-of-domain rejection, and global-safety preemption boundaries in `tests/integration/test_closed_vocabulary_stt.py`, `tests/integration/test_command_dialog_robustness.py`, and `tests/integration/test_runtime_failure_paths.py`
- [X] T023 [P] [US2] Add smoke coverage for closed-choice resolution, safe rejection, and prompt-echo quickstart paths in `tests/smoke/test_runtime_quickstart.py`

### Implementation for User Story 2

- [X] T024 [US2] Wire `core/closed_vocabulary.py` into recognition-time filtering and guided-answer validation in `core/stt.py` and `core/assistant_runtime.py`
- [X] T025 [US2] Implement prompt-echo suppression, retry-budget protection, and short-answer exceptions in `core/assistant_runtime.py`
- [X] T026 [US2] Keep unrelated non-safety commands inside the active guided context while honoring global safety preemption in `core/resolver.py` and `core/assistant_runtime.py`
- [X] T027 [US2] Emit structured guided-dialog outcomes for accepted answers, rejected answers, constrained retries, and prompt-echo suppressions in `core/command_models.py` and `core/assistant_runtime.py`
- [X] T028 [US2] Run US2 validation (`python -m pytest tests/unit/test_closed_vocabulary.py tests/unit/test_dialog_confirmation_policy.py tests/unit/test_assistant_runtime.py tests/integration/test_closed_vocabulary_stt.py tests/integration/test_command_dialog_robustness.py tests/integration/test_runtime_failure_paths.py tests/smoke/test_runtime_quickstart.py -q`) and record `SC-002` and `SC-003` evidence in `specs/016-voice-ux-guardrails/quickstart.md`

**Checkpoint**: User Stories 1 and 2 are independently functional and testable.

---

## Phase 5: User Story 3 - Complete Setup and Recovery Without Fragile Loops (Priority: P3)

**Goal**: Make onboarding, name confirmation, bounded fallback behavior, and pilot evidence collection complete end-to-end so non-completing journeys continue safely or exit gracefully with measurable outcomes.

**Independent Test**: Run end-to-end onboarding and settings journeys covering early answers, prompt echo, repeated invalid answers, mixed Arabic/English turns, and name confirmation recovery, then confirm names become final only after explicit confirmation, unconfirmed personalization is discarded, required settings continue with safe defaults when allowed, and pilot evidence captures completion, retries, suppressions, rejections, and fallback or exit reasons without raw utterances.

### Tests for User Story 3

- [X] T029 [P] [US3] Extend unit coverage for name-candidate confirmation, discard-on-rejection behavior, and safe-default continuation logic in `tests/unit/test_assistant_runtime.py`, `tests/unit/test_resolver.py`, and `tests/unit/test_runtime_contract.py`
- [X] T030 [P] [US3] Add integration coverage for mixed-language onboarding, repeated invalid answers, name confirmation recovery, and pilot evidence artifacts in `tests/integration/test_command_dialog_robustness.py`, `tests/integration/test_command_recognition_runtime.py`, and `tests/integration/test_release_journey_validation.py`
- [X] T031 [P] [US3] Add smoke coverage for end-to-end onboarding completion, safe-default continuation, and graceful-exit quickstart journeys in `tests/smoke/test_runtime_quickstart.py`

### Implementation for User Story 3

- [X] T032 [US3] Implement name-candidate lifecycle, explicit confirmation, and discard-on-rejection behavior in `core/assistant_runtime.py` and `core/command_models.py`
- [X] T033 [US3] Implement final-retry safe-default continuation and graceful-exit handling for required guided settings in `core/assistant_runtime.py`, `core/closed_vocabulary.py`, and `settings/settings_manager.py`
- [X] T034 [US3] Record pilot voice UX evidence bundles and field-safe summary outputs in `core/release_artifacts.py`, `core/release_metrics.py`, and `core/release_models.py`
- [X] T035 [US3] Document pilot acceptance checklist, tuning guidance, and evidence review expectations in `docs/release/checklist.md` and `specs/016-voice-ux-guardrails/quickstart.md`
- [X] T036 [US3] Run US3 validation (`python -m pytest tests/unit/test_assistant_runtime.py tests/unit/test_resolver.py tests/unit/test_runtime_contract.py tests/integration/test_command_dialog_robustness.py tests/integration/test_command_recognition_runtime.py tests/integration/test_release_journey_validation.py tests/smoke/test_runtime_quickstart.py -q`) and record `SC-004` and `SC-005` evidence in `specs/016-voice-ux-guardrails/quickstart.md` and `docs/release/checklist.md`

**Checkpoint**: All user stories are independently functional and validation-ready.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final contract alignment, runtime cleanup, and full feature verification across all stories.

- [X] T037 [P] Refresh Phase 16 contracts to match shipped turn-taking, closed-vocabulary, guided-dialog, and pilot-evidence payloads in `specs/016-voice-ux-guardrails/contracts/turn-taking-window-contract.md`, `specs/016-voice-ux-guardrails/contracts/closed-vocabulary-context-contract.md`, `specs/016-voice-ux-guardrails/contracts/guided-dialog-outcome-contract.md`, and `specs/016-voice-ux-guardrails/contracts/pilot-voice-ux-evaluation-contract.md`
- [X] T038 Remove stale inline guided-dialog logic that is superseded by the shared coordinator or registry in `core/assistant_runtime.py`, `core/stt.py`, and `core/resolver.py`
- [X] T039 [P] Add regression coverage for prompt-echo retry protection, global-safety preemption, name discard behavior, and field-safe pilot evidence in `tests/unit/test_closed_vocabulary.py`, `tests/integration/test_command_dialog_robustness.py`, and `tests/integration/test_release_journey_validation.py`
- [X] T040 Run the full validation sweep from `specs/016-voice-ux-guardrails/quickstart.md` (`python -m pytest tests/unit/test_turn_taking.py tests/unit/test_closed_vocabulary.py tests/unit/test_dialog_confirmation_policy.py tests/unit/test_assistant_runtime.py tests/unit/test_resolver.py tests/unit/test_runtime_contract.py tests/unit/test_tts_engine_interruptions.py -q`; `python -m pytest tests/integration/test_command_dialog_robustness.py tests/integration/test_closed_vocabulary_stt.py tests/integration/test_command_recognition_runtime.py tests/integration/test_runtime_interruptions.py tests/integration/test_runtime_failure_paths.py tests/integration/test_gui_runtime_bridge.py tests/integration/test_release_journey_validation.py -q`; `python -m pytest tests/smoke/test_runtime_quickstart.py -q`; `python -m compileall core tests`; `ruff check .`) and record outputs in `specs/016-voice-ux-guardrails/quickstart.md` and `docs/release/checklist.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on Foundational completion and integrates with the turn-taking and prompt surfaces established in US1, while remaining independently testable
- **User Story 3 (Phase 5)**: Depends on Foundational completion and should follow US1 and US2 so it measures the shipped guided dialog behavior rather than placeholder flows
- **Polish (Phase 6)**: Depends on completion of the user stories selected for release scope

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on other stories
- **US2 (P2)**: Starts after Foundational and builds on shared coordinator and registry boundaries; should be validated after US1 prompt-window behavior lands
- **US3 (P3)**: Starts after Foundational and should build on the guided answer and retry behavior delivered by US1 and US2

### Within Each User Story

- Write the listed tests first and confirm they fail before implementation
- Land shared runtime or contract updates before recording quickstart evidence
- Run the listed validation command and update `specs/016-voice-ux-guardrails/quickstart.md` before marking the story complete

### Parallel Opportunities

- `T002`, `T003`, and `T004` can run in parallel after `T001`
- `T006`, `T007`, `T009`, `T010`, `T011`, and `T012` can run in parallel after `T005`
- `T013`, `T014`, and `T015` can run in parallel for US1
- `T021`, `T022`, and `T023` can run in parallel for US2
- `T029`, `T030`, and `T031` can run in parallel for US3
- `T037` and `T039` can run in parallel during Polish

---

## Parallel Example: User Story 1

```bash
Task: "Extend unit coverage for eligible barge-in windows, protected prompt blocking, and prompt-class transitions in tests/unit/test_turn_taking.py, tests/unit/test_assistant_runtime.py, and tests/unit/test_tts_engine_interruptions.py"
Task: "Add integration coverage for early answers during onboarding or settings playback and protected-flow interruption blocking in tests/integration/test_command_recognition_runtime.py, tests/integration/test_runtime_interruptions.py, and tests/integration/test_gui_runtime_bridge.py"
Task: "Add smoke coverage for allowed early-answer and protected-prompt quickstart journeys in tests/smoke/test_runtime_quickstart.py"
```

## Parallel Example: User Story 2

```bash
Task: "Extend unit coverage for bilingual alias matching, closed-vocabulary retry limits, and prompt-echo suppression rules in tests/unit/test_closed_vocabulary.py, tests/unit/test_dialog_confirmation_policy.py, and tests/unit/test_assistant_runtime.py"
Task: "Add integration coverage for closed-vocabulary STT filtering, guided-context preservation, out-of-domain rejection, and global-safety preemption boundaries in tests/integration/test_closed_vocabulary_stt.py, tests/integration/test_command_dialog_robustness.py, and tests/integration/test_runtime_failure_paths.py"
Task: "Add smoke coverage for closed-choice resolution, safe rejection, and prompt-echo quickstart paths in tests/smoke/test_runtime_quickstart.py"
```

## Parallel Example: User Story 3

```bash
Task: "Extend unit coverage for name-candidate confirmation, discard-on-rejection behavior, and safe-default continuation logic in tests/unit/test_assistant_runtime.py, tests/unit/test_resolver.py, and tests/unit/test_runtime_contract.py"
Task: "Add integration coverage for mixed-language onboarding, repeated invalid answers, name confirmation recovery, and pilot evidence artifacts in tests/integration/test_command_dialog_robustness.py, tests/integration/test_command_recognition_runtime.py, and tests/integration/test_release_journey_validation.py"
Task: "Add smoke coverage for end-to-end onboarding completion, safe-default continuation, and graceful-exit quickstart journeys in tests/smoke/test_runtime_quickstart.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate allowed early answers and protected prompt blocking before widening scope

### Incremental Delivery

1. Setup + Foundational establish shared turn-taking, registry, prompt, settings, and structured-result boundaries
2. Deliver US1 for natural early answers with protected-flow safety
3. Deliver US2 for closed-vocabulary resolution, prompt-echo suppression, and safe guided-context preservation
4. Deliver US3 for explicit name confirmation, safe-default continuation, and pilot UX evidence
5. Finish with Phase 6 polish and the full validation sweep

### Parallel Team Strategy

1. Team aligns on Setup and Foundational together
2. After Phase 2:
   - Developer A: US1 turn-taking coordinator integration and protected prompt boundaries
   - Developer B: US2 closed-vocabulary registry, STT filtering, and prompt-echo safe rejection
   - Developer C: US3 name candidate flow, pilot evidence artifacts, and acceptance checklist
3. Rejoin for cross-cutting cleanup and full validation

---

## Notes

- `[P]` tasks are parallel-safe only after their prerequisite tasks are complete
- Every user story includes explicit test tasks because this feature touches runtime safety, resolver behavior, STT filtering, prompt playback, and field-safe evidence generation
- Keep guided voice authority in `core/`, `settings/`, and `tts/`; GUI surfaces should observe the same behavior instead of defining a separate dialog model
- Default pilot evidence must remain local and field-safe, without raw user utterances unless a separately approved fixture workflow is used
