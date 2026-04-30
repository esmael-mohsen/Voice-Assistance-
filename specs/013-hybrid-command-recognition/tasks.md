# Tasks: Hybrid Command Recognition and Post-Processing

**Input**: Design documents from `/specs/013-hybrid-command-recognition/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are REQUIRED because this feature changes STT behavior, parser
pre-processing, dispatcher and resolver safety, runtime orchestration, settings
application, and command-recognition telemetry.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this belongs to (e.g. `US1`, `US2`, `US3`)
- Include exact file paths in descriptions

## Path Conventions

- **Current project layout**: `main.py`, `controllers/`, `core/`, `settings/`, `tts/`, `ui/`, `tests/`, `docs/`, `scripts/`
- **Feature focus**: command recognition in `core/stt.py`, runtime confidence flow in `core/assistant_runtime.py`, parser and dispatcher plumbing in `core/parser.py`, `core/dispatcher.py`, and `core/resolver.py`, command contracts in `core/command_models.py`, runtime settings in `settings/settings_manager.py`, and a dedicated command post-processing boundary under `core/`
- **Specification docs**: `specs/013-hybrid-command-recognition/contracts/` and `specs/013-hybrid-command-recognition/quickstart.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare Phase 13 fixtures, regression entry points, and quickstart evidence placeholders.

- [X] T001 Add Phase 13 command-recognition fixtures, transcript samples, and runtime observer helpers in `tests/conftest.py`
- [X] T002 [P] Create Phase 13 unit scaffolding in `tests/unit/test_command_recognition_contract.py`, `tests/unit/test_command_post_processing.py`, `tests/unit/test_command_confidence_policy.py`, and `tests/unit/test_assistant_runtime.py`
- [X] T003 [P] Create Phase 13 integration scaffolding in `tests/integration/test_command_recognition_runtime.py`, `tests/integration/test_command_dispatch.py`, `tests/integration/test_command_dialog_robustness.py`, and `tests/integration/test_gui_runtime_bridge.py`
- [X] T004 [P] Create Phase 13 smoke scaffolding in `tests/smoke/test_hybrid_command_recognition_quickstart.py` and add validation evidence placeholders in `specs/013-hybrid-command-recognition/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared recognition-result, post-processing, confidence-policy, and telemetry boundaries required by all user stories.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Add failing unit coverage for structured command-recognition results, missing-confidence handling, and fallback-path metadata in `tests/unit/test_command_recognition_contract.py` and `tests/unit/test_assistant_runtime.py`
- [X] T006 [P] Add failing unit coverage for transcript normalization, bilingual substitutions, and canonical command text generation in `tests/unit/test_command_post_processing.py` and `tests/unit/test_parser.py`
- [X] T007 [P] Add failing unit coverage for confidence-band decisions, bounded retry policy, and protected-command confirmation rules in `tests/unit/test_command_confidence_policy.py`, `tests/unit/test_resolver.py`, and `tests/unit/test_assistant_runtime.py`
- [X] T008 [P] Add failing integration coverage for local-first recognition flow, fallback escalation, and offline-safe command handling in `tests/integration/test_command_recognition_runtime.py`, `tests/integration/test_runtime_offline_behavior.py`, and `tests/integration/test_runtime_modes.py`
- [X] T009 [P] Add failing integration coverage for protected-command confirmation and GUI or headless parity in `tests/integration/test_command_dialog_robustness.py`, `tests/integration/test_command_confirmation_localization.py`, and `tests/integration/test_gui_runtime_bridge.py`
- [X] T010 [P] Add failing smoke coverage for local-first, fallback, and bilingual quickstart journeys in `tests/smoke/test_hybrid_command_recognition_quickstart.py`, `tests/smoke/test_command_layer_quickstart.py`, and `tests/smoke/test_confirmation_clarification_quickstart.py`
- [X] T011 Define the explicit local/fallback recognizer contract plus `CommandRecognitionResult`, `CommandPostProcessingOutcome`, `ConfidenceDecisionPolicy`, and `RecognitionTelemetrySample` models in `core/stt.py` and `core/command_models.py`
- [X] T012 [P] Add a dedicated command post-processing module with normalization and canonicalization helpers in `core/command_post_processing.py`
- [X] T013 [P] Add runtime settings snapshot fields for confidence thresholds, fallback enablement, and local-only command policy in `settings/settings_manager.py` and `settings/profile_store.py`
- [X] T014 [P] Add shared telemetry and decision-shaping helpers for command recognition in `core/assistant_runtime.py` and `core/dispatcher.py`

**Checkpoint**: Shared recognition contracts, post-processing boundary, and confidence-policy plumbing are ready; user story work can begin.

---

## Phase 3: User Story 1 - Recognize Common Commands Quickly (Priority: P1) MVP

**Goal**: Ensure supported Arabic and English commands complete through a fast local-first path with structured recognition results and safe offline local handling.

**Independent Test**: Run representative Arabic and English command trials with network available and unavailable, then confirm supported high-confidence commands complete through the first recognition path without unnecessary fallback or extra prompts.

### Tests for User Story 1

> **NOTE: Write these tests FIRST and ensure they fail before implementation
> because this story changes constitution-protected parser, dispatcher, runtime,
> settings, and STT behavior.**

- [X] T015 [P] [US1] Extend unit coverage for local-first recognition result shaping and no-confidence non-protected execution rules in `tests/unit/test_command_recognition_contract.py`, `tests/unit/test_assistant_runtime.py`, and `tests/unit/test_parser.py`
- [X] T016 [P] [US1] Add integration coverage for high-confidence local-first command execution and offline-safe local handling in `tests/integration/test_command_recognition_runtime.py`, `tests/integration/test_command_dispatch.py`, and `tests/integration/test_runtime_offline_behavior.py`
- [X] T017 [P] [US1] Add smoke coverage for the high-confidence local-first quickstart path in `tests/smoke/test_hybrid_command_recognition_quickstart.py` and `tests/smoke/test_command_layer_quickstart.py`

### Implementation for User Story 1

- [X] T018 [US1] Extend `VoiceListener` and the local/fallback recognizer boundary to return structured command-recognition results with transcript, confidence, alternatives, mixed-language candidate support, source metadata, and latency in `core/stt.py`
- [X] T019 [US1] Wire local-first command recognition through the runtime session window and command intake flow in `core/assistant_runtime.py`
- [X] T020 [US1] Teach dispatcher and parser entrypoints to accept canonical command text and recognition metadata in `core/dispatcher.py` and `core/parser.py`
- [X] T021 [US1] Preserve truthful local-only offline execution for supported commands when fallback is unavailable in `core/assistant_runtime.py`, `core/resolver.py`, and `settings/settings_manager.py`
- [X] T022 [US1] Run US1 validation (`python -m pytest tests/unit/test_command_recognition_contract.py tests/unit/test_assistant_runtime.py tests/unit/test_parser.py tests/integration/test_command_recognition_runtime.py tests/integration/test_command_dispatch.py tests/integration/test_runtime_offline_behavior.py tests/smoke/test_hybrid_command_recognition_quickstart.py tests/smoke/test_command_layer_quickstart.py -q`) and record SC-001 and SC-004 evidence in `specs/013-hybrid-command-recognition/quickstart.md`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Handle Uncertain Commands Safely (Priority: P2)

**Goal**: Ensure medium-confidence, low-confidence, and ambiguous commands trigger bounded fallback, confirmation, retry, deferral, or safe refusal without unsafe silent execution.

**Independent Test**: Exercise medium-confidence, low-confidence, and ambiguous command trials for ordinary and protected intents, then confirm the assistant escalates, confirms, retries once, or refuses according to the confidence band.

### Tests for User Story 2

- [X] T023 [P] [US2] Extend unit coverage for confidence-band evaluation, bounded retry limits, and protected-command confirmation thresholds in `tests/unit/test_command_confidence_policy.py`, `tests/unit/test_resolver.py`, and `tests/unit/test_assistant_runtime.py`
- [X] T024 [P] [US2] Add integration coverage for fallback escalation, protected-command confirmation, mixed-language uncertain commands, and fallback-unavailable safe refusal in `tests/integration/test_command_recognition_runtime.py`, `tests/integration/test_command_dialog_robustness.py`, and `tests/integration/test_command_confirmation_localization.py`
- [X] T025 [P] [US2] Add GUI or headless parity coverage for uncertain-command handling in `tests/integration/test_gui_runtime_bridge.py` and `tests/integration/test_runtime_modes.py`
- [X] T026 [P] [US2] Add smoke coverage for confidence-aware fallback and protected-command safety in `tests/smoke/test_hybrid_command_recognition_quickstart.py` and `tests/smoke/test_confirmation_clarification_quickstart.py`

### Implementation for User Story 2

- [X] T027 [US2] Add confidence-band decision evaluation and fallback escalation flow in `core/assistant_runtime.py` and `core/command_models.py`
- [X] T028 [US2] Reuse resolver confirmation and clarification paths for confidence-aware protected-command handling and one-cycle retry limits in `core/resolver.py` and `core/assistant_runtime.py`
- [X] T029 [US2] Add fallback-recognition orchestration, mixed-language uncertain-command handling, and failure or timeout handling around uncertain commands in `core/stt.py` and `core/assistant_runtime.py`
- [X] T030 [US2] Persist and expose command-confidence policy values through runtime settings snapshots in `settings/settings_manager.py` and `settings/profile_store.py`
- [X] T031 [US2] Run US2 validation (`python -m pytest tests/unit/test_command_confidence_policy.py tests/unit/test_resolver.py tests/unit/test_assistant_runtime.py tests/integration/test_command_recognition_runtime.py tests/integration/test_command_dialog_robustness.py tests/integration/test_command_confirmation_localization.py tests/integration/test_gui_runtime_bridge.py tests/integration/test_runtime_modes.py tests/smoke/test_hybrid_command_recognition_quickstart.py tests/smoke/test_confirmation_clarification_quickstart.py -q`) and record SC-002 and SC-003 evidence in `specs/013-hybrid-command-recognition/quickstart.md`

**Checkpoint**: User Stories 1 and 2 are independently functional and testable.

---

## Phase 5: User Story 3 - Normalize Noisy Bilingual Speech Consistently (Priority: P3)

**Goal**: Normalize common Arabic and English STT substitutions before parsing and emit metadata-first telemetry that explains recognition-path decisions and latency impact.

**Independent Test**: Run a regression set containing noisy transcripts, Arabic-English switching, and common substitution patterns, then confirm canonical command text and telemetry stay consistent across equivalent inputs and fallback-assisted interactions.

### Tests for User Story 3

- [X] T032 [P] [US3] Extend unit coverage for bilingual substitutions, canonical command text generation, and ambiguity-flag emission in `tests/unit/test_command_post_processing.py`, `tests/unit/test_parser.py`, and `tests/unit/test_command_recognition_contract.py`
- [X] T033 [P] [US3] Add integration coverage for parser inputs sourced from post-processing, mixed-language recognition continuity, and metadata-first telemetry emission in `tests/integration/test_command_dispatch.py`, `tests/integration/test_command_recognition_runtime.py`, and `tests/integration/test_runtime_modes.py`
- [X] T034 [P] [US3] Add smoke coverage for noisy bilingual quickstart journeys and telemetry review in `tests/smoke/test_hybrid_command_recognition_quickstart.py` and `tests/smoke/test_runtime_quickstart.py`

### Implementation for User Story 3

- [X] T035 [US3] Implement Arabic and English substitution repair, bilingual normalization, and canonical command phrase generation in `core/command_post_processing.py`
- [X] T036 [US3] Thread post-processing outcomes and canonical command text into parser and dispatcher flows in `core/parser.py`, `core/dispatcher.py`, and `core/assistant_runtime.py`
- [X] T037 [US3] Emit metadata-first command-recognition telemetry with session identifier, recognition path, confidence band, fallback usage, decision outcome, protected-command flag, latency impact, and 95th-percentile latency evidence inputs in `core/assistant_runtime.py` and `core/command_models.py`
- [X] T038 [US3] Run US3 validation with the `SC-005` latency protocol (`30` local-first trials and `30` fallback-assisted trials per validation run, measured from recognition start to spoken-response start, plus `python -m pytest tests/unit/test_command_post_processing.py tests/unit/test_parser.py tests/unit/test_command_recognition_contract.py tests/integration/test_command_dispatch.py tests/integration/test_command_recognition_runtime.py tests/integration/test_runtime_modes.py tests/smoke/test_hybrid_command_recognition_quickstart.py tests/smoke/test_runtime_quickstart.py -q`) and record SC-005 and SC-006 evidence in `specs/013-hybrid-command-recognition/quickstart.md`

**Checkpoint**: All user stories are independently functional and testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final contract alignment, regression hardening, latency validation, and full feature verification across all stories.

- [X] T039 [P] Refresh Phase 13 contracts to match shipped recognition-result, post-processing, and confidence-decision payloads in `specs/013-hybrid-command-recognition/contracts/command-recognition-result-contract.md`, `specs/013-hybrid-command-recognition/contracts/command-post-processing-contract.md`, and `specs/013-hybrid-command-recognition/contracts/command-confidence-decision-contract.md`
- [X] T040 Remove stale raw-string command-intake shortcuts and duplicated normalization assumptions in `core/stt.py`, `core/parser.py`, `core/dispatcher.py`, `core/resolver.py`, and `core/assistant_runtime.py`
- [X] T041 [P] Add regression coverage for missing confidence, conflicting alternatives, fallback timeout, mixed-language command switching, percentile latency evidence, and metadata-only telemetry defaults in `tests/unit/test_command_confidence_policy.py`, `tests/unit/test_command_post_processing.py`, `tests/integration/test_command_recognition_runtime.py`, `tests/integration/test_gui_runtime_bridge.py`, and `tests/smoke/test_hybrid_command_recognition_quickstart.py`
- [X] T042 Run full validation sweep (`python -m pytest tests/unit/test_command_recognition_contract.py tests/unit/test_command_post_processing.py tests/unit/test_command_confidence_policy.py tests/unit/test_assistant_runtime.py tests/unit/test_parser.py tests/unit/test_resolver.py -q`, `python -m pytest tests/integration/test_command_recognition_runtime.py tests/integration/test_command_dispatch.py tests/integration/test_command_dialog_robustness.py tests/integration/test_command_confirmation_localization.py tests/integration/test_gui_runtime_bridge.py tests/integration/test_runtime_modes.py tests/integration/test_runtime_offline_behavior.py -q`, `python -m pytest tests/smoke/test_hybrid_command_recognition_quickstart.py tests/smoke/test_command_layer_quickstart.py tests/smoke/test_confirmation_clarification_quickstart.py tests/smoke/test_runtime_quickstart.py -q`, `python -m compileall core tests`, `ruff check .`) and record outputs in `specs/013-hybrid-command-recognition/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories
- **User Stories (Phases 3-5)**: Depend on Foundational completion
- **Polish (Phase 6)**: Depends on completion of the user stories selected for release scope

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on other stories
- **US2 (P2)**: Starts after Foundational; builds on shared recognition-result and confidence-policy boundaries but remains independently testable
- **US3 (P3)**: Starts after Foundational; its full telemetry and canonicalization pass should run after the local-first and confidence-decision flows are in place

### Within Each User Story

- Write the listed tests first and confirm they fail before implementation
- Land shared command-recognition and confidence-policy updates before story-specific smoke validation
- Run the listed validation command and record evidence in `specs/013-hybrid-command-recognition/quickstart.md` before marking the story complete

### Parallel Opportunities

- `T002`, `T003`, and `T004` can run in parallel after `T001`
- `T006`, `T007`, `T008`, `T009`, `T010`, `T012`, `T013`, and `T014` can run in parallel after `T005`
- `T015`, `T016`, and `T017` can run in parallel for US1
- `T023`, `T024`, `T025`, and `T026` can run in parallel for US2
- `T032`, `T033`, and `T034` can run in parallel for US3
- `T039` and `T041` can run in parallel during Polish

---

## Parallel Example: User Story 1

```bash
Task: "Extend unit coverage for local-first recognition result shaping and no-confidence non-protected execution rules in tests/unit/test_command_recognition_contract.py, tests/unit/test_assistant_runtime.py, and tests/unit/test_parser.py"
Task: "Add integration coverage for high-confidence local-first command execution and offline-safe local handling in tests/integration/test_command_recognition_runtime.py, tests/integration/test_command_dispatch.py, and tests/integration/test_runtime_offline_behavior.py"
Task: "Add smoke coverage for the high-confidence local-first quickstart path in tests/smoke/test_hybrid_command_recognition_quickstart.py and tests/smoke/test_command_layer_quickstart.py"
```

## Parallel Example: User Story 2

```bash
Task: "Extend unit coverage for confidence-band evaluation, bounded retry limits, and protected-command confirmation thresholds in tests/unit/test_command_confidence_policy.py, tests/unit/test_resolver.py, and tests/unit/test_assistant_runtime.py"
Task: "Add integration coverage for fallback escalation, protected-command confirmation, and fallback-unavailable safe refusal in tests/integration/test_command_recognition_runtime.py, tests/integration/test_command_dialog_robustness.py, and tests/integration/test_command_confirmation_localization.py"
Task: "Add GUI/headless parity coverage for uncertain-command handling in tests/integration/test_gui_runtime_bridge.py and tests/integration/test_runtime_modes.py"
Task: "Add smoke coverage for confidence-aware fallback and protected-command safety in tests/smoke/test_hybrid_command_recognition_quickstart.py and tests/smoke/test_confirmation_clarification_quickstart.py"
```

## Parallel Example: User Story 3

```bash
Task: "Extend unit coverage for bilingual substitutions, canonical command text generation, and ambiguity-flag emission in tests/unit/test_command_post_processing.py, tests/unit/test_parser.py, and tests/unit/test_command_recognition_contract.py"
Task: "Add integration coverage for parser inputs sourced from post-processing and metadata-first telemetry emission in tests/integration/test_command_dispatch.py, tests/integration/test_command_recognition_runtime.py, and tests/integration/test_runtime_modes.py"
Task: "Add smoke coverage for noisy bilingual quickstart journeys and telemetry review in tests/smoke/test_hybrid_command_recognition_quickstart.py and tests/smoke/test_runtime_quickstart.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate fast local-first command execution before widening scope

### Incremental Delivery

1. Setup + Foundational establish structured recognition results, post-processing boundaries, confidence-policy settings, and telemetry helpers
2. Deliver US1 for local-first command execution and safe offline local handling
3. Deliver US2 for confidence-aware fallback, bounded retry, and protected-command safety
4. Deliver US3 for noisy bilingual normalization and metadata-first recognition telemetry
5. Finish with Phase 6 polish and the full validation sweep

### Parallel Team Strategy

1. Team aligns on Setup and Foundational together
2. After Phase 2:
   - Developer A: US1 local-first recognition and dispatcher plumbing
   - Developer B: US2 confidence decisions, fallback flow, and protected-command safeguards
   - Developer C: US3 post-processing rules, telemetry emission, and regression evidence
3. Rejoin for cross-cutting cleanup and final validation

---

## Notes

- `[P]` tasks are parallel-safe only after their dependency prerequisites are complete
- Every user story includes explicit test tasks because this feature touches parser, resolver, dispatcher, runtime safety, settings application, and observability
- Keep command meaning runtime-owned; GUI paths must consume the same recognition and confidence-decision flow rather than creating a separate interpretation layer
- Default telemetry and artifacts must remain metadata-first and must not expose raw user utterances unless a narrower future requirement explicitly approves that path
