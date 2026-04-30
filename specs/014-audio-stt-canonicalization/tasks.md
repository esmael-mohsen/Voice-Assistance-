# Tasks: Audio Front-End, Hybrid STT, and Command Canonicalization

**Input**: Design documents from `/specs/014-audio-stt-canonicalization/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are REQUIRED because this feature changes STT behavior, audio
capture policy, parser pre-processing, runtime orchestration, settings
application, provider adapters, and safety-critical degraded-mode handling.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this belongs to (e.g. `US1`, `US2`, `US3`)
- Include exact file paths in descriptions

## Path Conventions

- **Current project layout**: `main.py`, `controllers/`, `core/`, `settings/`, `tts/`, `ui/`, `tests/`, `docs/`, `scripts/`
- **Feature focus**: audio capture and recognition in `core/stt.py`, `core/speech/legacy_stt.py`, and the new `core/audio/` package; runtime orchestration in `core/assistant_runtime.py`; canonicalization in `core/command_post_processing.py`; runtime settings in `settings/settings_manager.py` and `settings/profile_store.py`
- **Specification docs**: `specs/014-audio-stt-canonicalization/contracts/` and `specs/014-audio-stt-canonicalization/quickstart.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare Phase 14 fixture registries, test entry points, and qualification evidence placeholders.

- [X] T001 Add Phase 14 curated audio fixture registry and qualification profile helpers in `tests/conftest.py` and `tests/fixtures/audio/README.md`
- [X] T002 [P] Create Phase 14 unit-test scaffolding in `tests/unit/test_audio_preprocessing.py`, `tests/unit/test_capture_profiles.py`, `tests/unit/test_capture_quality_metadata_contract.py`, `tests/unit/test_hybrid_command_recognition_contract.py`, and `tests/unit/test_command_canonicalization.py`
- [X] T003 [P] Create Phase 14 integration-test scaffolding in `tests/integration/test_command_capture_endpointing.py`, `tests/integration/test_hybrid_command_recognition.py`, and `tests/integration/test_closed_vocabulary_stt.py`
- [X] T004 [P] Create Phase 14 smoke scaffolding and qualification evidence placeholders, including recommended local-first stack and tradeoff sections, in `tests/smoke/test_audio_frontend_quickstart.py`, `docs/release/audio_frontend_qualification.md`, and `specs/014-audio-stt-canonicalization/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared audio-profile, preprocessing, structured recognition, and qualification boundaries required by all user stories.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Add failing unit coverage for capture profiles, audio preprocessing normalization, and capture-quality metadata contracts in `tests/unit/test_capture_profiles.py`, `tests/unit/test_audio_preprocessing.py`, and `tests/unit/test_capture_quality_metadata_contract.py`
- [X] T006 [P] Add failing unit coverage for hybrid recognition contracts, parser-ready canonicalization, and disagreement handling in `tests/unit/test_hybrid_command_recognition_contract.py`, `tests/unit/test_command_canonicalization.py`, and `tests/unit/test_parser.py`
- [X] T007 [P] Add failing integration coverage for endpoint-aware capture, bounded relisten, and mode-specific profile selection in `tests/integration/test_command_capture_endpointing.py`, `tests/integration/test_runtime_modes.py`, and `tests/integration/test_gui_runtime_bridge.py`
- [X] T008 [P] Add failing integration coverage for local-first or rescue routing, closed-vocabulary filtering, and degraded-mode truthfulness in `tests/integration/test_hybrid_command_recognition.py`, `tests/integration/test_closed_vocabulary_stt.py`, and `tests/integration/test_runtime_offline_behavior.py`
- [X] T009 [P] Add failing smoke coverage for capture recovery, local-first command mode, and simplified-profile behavior in `tests/smoke/test_audio_frontend_quickstart.py`, `tests/smoke/test_hybrid_command_recognition_quickstart.py`, and `tests/smoke/test_runtime_quickstart.py`
- [X] T010 Define `AudioCaptureProfile`, `AudioCaptureAttempt`, `HybridRecognitionResult`, and qualification-facing model fields in `core/command_models.py` and `core/speech/interfaces.py`
- [X] T011 [P] Create the shared audio profile and package scaffolding in `core/audio/__init__.py` and `core/audio/profiles.py`
- [X] T012 [P] Implement reusable preprocessing and endpoint-quality helpers in `core/audio/preprocessing.py` and `core/audio/endpointing.py`
- [X] T013 [P] Add capture-profile, rescue-toggle, and qualification-profile settings fields in `settings/settings_manager.py` and `settings/profile_store.py`
- [X] T014 [P] Update the legacy speech-provider boundary to accept capture profiles and structured recognition metadata in `core/speech/legacy_stt.py` and `core/speech/provider_registry.py`
- [X] T015 [P] Add shared profile-aware telemetry and qualification helper plumbing in `core/assistant_runtime.py` and `core/runtime_diagnostics.py`

**Checkpoint**: Shared audio, recognition, settings, and observability boundaries are ready; user story work can begin.

---

## Phase 3: User Story 1 - Capture Complete Spoken Requests (Priority: P1) MVP

**Goal**: Capture full spoken requests with profile-driven preprocessing, endpoint-aware metadata, and one bounded clipped-utterance recovery path.

**Independent Test**: Run wearable-style command trials with soft starts, brief pauses, and quiet endings, then confirm the assistant preserves the full utterance, emits capture-quality metadata, and uses at most one short relisten when clipping is suspected.

### Tests for User Story 1

> **NOTE: Write these tests FIRST and ensure they fail before implementation
> because this story changes constitution-protected STT, runtime, settings, and
> headless interaction behavior.**

- [X] T016 [P] [US1] Extend unit coverage for clipping detection, capture metadata emission, and one-relisten limits in `tests/unit/test_audio_preprocessing.py`, `tests/unit/test_capture_quality_metadata_contract.py`, and `tests/unit/test_assistant_runtime.py`
- [X] T017 [P] [US1] Add integration coverage for command capture profiles, endpoint padding, and bounded relisten recovery in `tests/integration/test_command_capture_endpointing.py` and `tests/integration/test_gui_runtime_bridge.py`
- [X] T018 [P] [US1] Add smoke coverage for clipped-utterance recovery and capture completeness in `tests/smoke/test_audio_frontend_quickstart.py` and `tests/smoke/test_runtime_quickstart.py`

### Implementation for User Story 1

- [X] T019 [US1] Wire standby, onboarding, command, and confirmation capture-profile selection through `VoiceListener` in `core/stt.py` and `core/audio/profiles.py`
- [X] T020 [US1] Apply preprocessing, endpoint padding, and clipping-hint generation to command capture in `core/stt.py`, `core/audio/preprocessing.py`, and `core/audio/endpointing.py`
- [X] T021 [US1] Implement bounded clipped-utterance relisten and short recovery prompts in `core/assistant_runtime.py` and `core/stt.py`
- [X] T022 [US1] Thread capture-quality metadata into runtime recovery and command dispatch decisions in `core/assistant_runtime.py`, `core/dispatcher.py`, and `core/command_models.py`
- [X] T023 [US1] Run US1 validation (`python -m pytest tests/unit/test_audio_preprocessing.py tests/unit/test_capture_quality_metadata_contract.py tests/unit/test_assistant_runtime.py tests/integration/test_command_capture_endpointing.py tests/integration/test_gui_runtime_bridge.py tests/smoke/test_audio_frontend_quickstart.py tests/smoke/test_runtime_quickstart.py -q`) and record `SC-001` evidence in `specs/014-audio-stt-canonicalization/quickstart.md` and `docs/release/audio_frontend_qualification.md`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Recognize Commands Reliably in Noisy Bilingual Use (Priority: P2)

**Goal**: Prefer a practical local-first recognition path, use bounded rescue recognition only on uncertainty, and keep noisy bilingual transcripts inside the supported command space and constrained answer sets.

**Independent Test**: Run noisy local samples, Arabic-English mixed commands, and closed-vocabulary onboarding or yes-no flows, then confirm the assistant prefers the local-first path, uses rescue only when needed, handles disagreement safely, and returns to the prior safe step after one constrained retry.

### Tests for User Story 2

- [X] T024 [P] [US2] Extend unit coverage for local-first or rescue result shaping, language candidates, and disagreement handling in `tests/unit/test_hybrid_command_recognition_contract.py`, `tests/unit/test_assistant_runtime.py`, and `tests/unit/test_command_canonicalization.py`
- [X] T025 [P] [US2] Add integration coverage for Vosk-first routing, rescue escalation, and recognition-path disagreement handling in `tests/integration/test_hybrid_command_recognition.py`, `tests/integration/test_command_dispatch.py`, and `tests/integration/test_runtime_offline_behavior.py`
- [X] T026 [P] [US2] Add integration coverage for closed-vocabulary filtering, constrained retry, and truthful degraded-mode messages in `tests/integration/test_closed_vocabulary_stt.py`, `tests/integration/test_runtime_modes.py`, and `tests/integration/test_gui_runtime_bridge.py`
- [X] T027 [P] [US2] Add smoke coverage for local-first, rescue, and closed-choice quickstart journeys in `tests/smoke/test_audio_frontend_quickstart.py` and `tests/smoke/test_hybrid_command_recognition_quickstart.py`

### Implementation for User Story 2

- [X] T028 [US2] Make Vosk the preferred local-first command recognizer with bounded compatibility fallback in `core/stt.py` and `core/speech/legacy_stt.py`
- [X] T029 [US2] Implement rescue-recognition gating, disagreement resolution, and truthful degraded-mode handling in `core/assistant_runtime.py` and `core/stt.py`
- [X] T030 [US2] Extend transcript canonicalization with bilingual aliases, confusion pairs, and mode-specific dictionary filtering in `core/command_post_processing.py` and `core/parser.py`
- [X] T031 [US2] Thread `closed_vocabulary_id`, dictionary-bias metadata, and canonical command text through runtime dispatch in `core/assistant_runtime.py`, `core/dispatcher.py`, and `core/command_models.py`
- [X] T032 [US2] Run US2 validation (`python -m pytest tests/unit/test_hybrid_command_recognition_contract.py tests/unit/test_command_canonicalization.py tests/unit/test_assistant_runtime.py tests/integration/test_hybrid_command_recognition.py tests/integration/test_closed_vocabulary_stt.py tests/integration/test_command_dispatch.py tests/integration/test_runtime_modes.py tests/integration/test_runtime_offline_behavior.py tests/smoke/test_audio_frontend_quickstart.py tests/smoke/test_hybrid_command_recognition_quickstart.py -q`) and record `SC-002`, `SC-003`, and `SC-004` evidence in `specs/014-audio-stt-canonicalization/quickstart.md` and `docs/release/audio_frontend_qualification.md`

**Checkpoint**: User Stories 1 and 2 are functional and independently verifiable.

---

## Phase 5: User Story 3 - Qualify Speech Quality on Raspberry Pi 4 (Priority: P3)

**Goal**: Prove the upgraded speech stack improves capture and recognition quality while staying within Raspberry Pi 4 budgets, and publish truthful metadata-first qualification evidence.

**Independent Test**: Run the maintained benchmark set against the default and simplified qualification profiles, then confirm capture completeness, accuracy, and latency are recorded, and any optional enhancement that breaches the Pi 4 budget is demoted explicitly instead of remaining enabled silently.

### Tests for User Story 3

- [X] T033 [P] [US3] Extend unit coverage for qualification-profile selection, enhancement-demotion rules, and field-safe evidence shaping in `tests/unit/test_capture_profiles.py`, `tests/unit/test_assistant_runtime.py`, and `tests/unit/test_hybrid_command_recognition_contract.py`
- [X] T034 [P] [US3] Add integration coverage for simplified-profile behavior, optional-enhancement demotion, and qualification telemetry emission in `tests/integration/test_hybrid_command_recognition.py`, `tests/integration/test_runtime_modes.py`, and `tests/integration/test_gui_runtime_bridge.py`
- [X] T035 [P] [US3] Add smoke coverage for default-vs-simplified qualification runs in `tests/smoke/test_audio_frontend_quickstart.py` and `tests/smoke/test_runtime_quickstart.py`

### Implementation for User Story 3

- [X] T036 [US3] Implement qualification-profile selection and optional-enhancement demotion policy in `settings/settings_manager.py`, `settings/profile_store.py`, and `core/assistant_runtime.py`
- [X] T037 [US3] Add metadata-first qualification telemetry and evidence aggregation for capture completeness, accuracy, and latency in `core/assistant_runtime.py`, `core/runtime_diagnostics.py`, and `core/release_metrics.py`
- [X] T038 [US3] Add curated offline benchmark fixture manifests plus the recommended free local-first speech stack and Raspberry Pi 4 tradeoff guidance in `tests/fixtures/audio/README.md`, `tests/conftest.py`, and `docs/release/audio_frontend_qualification.md`
- [X] T039 [US3] Run US3 validation (`python -m pytest tests/unit/test_capture_profiles.py tests/unit/test_assistant_runtime.py tests/unit/test_hybrid_command_recognition_contract.py tests/integration/test_hybrid_command_recognition.py tests/integration/test_runtime_modes.py tests/integration/test_gui_runtime_bridge.py tests/smoke/test_audio_frontend_quickstart.py tests/smoke/test_runtime_quickstart.py -q` plus the `30`-trial local-first and `30`-trial rescue-path qualification protocol) and record `SC-005`, `SC-006`, and `SC-007` evidence in `specs/014-audio-stt-canonicalization/quickstart.md` and `docs/release/audio_frontend_qualification.md`

**Checkpoint**: All user stories are independently functional and qualification-ready.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final contract alignment, regression hardening, and full feature verification across all stories.

- [X] T040 [P] Refresh Phase 14 contracts to match shipped capture-profile, capture-metadata, hybrid-recognition, and canonicalization payloads in `specs/014-audio-stt-canonicalization/contracts/audio-capture-profile-contract.md`, `specs/014-audio-stt-canonicalization/contracts/capture-quality-metadata-contract.md`, `specs/014-audio-stt-canonicalization/contracts/hybrid-command-recognition-contract.md`, and `specs/014-audio-stt-canonicalization/contracts/transcript-canonicalization-contract.md`
- [X] T041 Remove stale string-only or unrestricted free-text shortcuts that bypass capture profiles, closed-vocabulary filtering, or canonicalization in `core/stt.py`, `core/speech/legacy_stt.py`, `core/parser.py`, and `core/assistant_runtime.py`
- [X] T042 [P] Add regression coverage for confusion pairs, out-of-set retries, profile demotion, and field-safe telemetry defaults in `tests/unit/test_command_canonicalization.py`, `tests/integration/test_closed_vocabulary_stt.py`, and `tests/smoke/test_audio_frontend_quickstart.py`
- [X] T043 Run the full validation sweep from `specs/014-audio-stt-canonicalization/quickstart.md` (`python -m pytest tests/unit/test_audio_preprocessing.py tests/unit/test_capture_profiles.py tests/unit/test_capture_quality_metadata_contract.py tests/unit/test_hybrid_command_recognition_contract.py tests/unit/test_command_canonicalization.py -q`; `python -m pytest tests/integration/test_command_capture_endpointing.py tests/integration/test_hybrid_command_recognition.py tests/integration/test_closed_vocabulary_stt.py tests/integration/test_runtime_modes.py tests/integration/test_runtime_offline_behavior.py tests/integration/test_gui_runtime_bridge.py -q`; `python -m pytest tests/smoke/test_audio_frontend_quickstart.py tests/smoke/test_hybrid_command_recognition_quickstart.py tests/smoke/test_runtime_quickstart.py -q`; `python -m compileall core tests`; `ruff check .`) and record outputs in `specs/014-audio-stt-canonicalization/quickstart.md` and `docs/release/audio_frontend_qualification.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on User Story 1 capture-path wiring plus Foundational completion
- **User Story 3 (Phase 5)**: Depends on User Stories 1 and 2 because qualification measures the shipped capture and hybrid-recognition behavior
- **Polish (Phase 6)**: Depends on completion of the user stories selected for release scope

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on other stories
- **US2 (P2)**: Builds on the capture-aware command path from US1 and adds hybrid recognition, constrained-mode handling, and canonicalization behavior
- **US3 (P3)**: Builds on US1 and US2 to qualify the shipped profiles and publish Pi 4 evidence

### Within Each User Story

- Write the listed tests first and confirm they fail before implementation
- Land the story's runtime and contract plumbing before recording quickstart evidence
- Run the listed validation command and update `specs/014-audio-stt-canonicalization/quickstart.md` before marking the story complete

### Parallel Opportunities

- `T002`, `T003`, and `T004` can run in parallel after `T001`
- `T006`, `T007`, `T008`, `T009`, `T011`, `T012`, `T013`, `T014`, and `T015` can run in parallel after `T005`
- `T016`, `T017`, and `T018` can run in parallel for US1
- `T024`, `T025`, `T026`, and `T027` can run in parallel for US2
- `T033`, `T034`, and `T035` can run in parallel for US3
- `T040` and `T042` can run in parallel during Polish

---

## Parallel Example: User Story 1

```bash
Task: "Extend unit coverage for clipping detection, capture metadata emission, and one-relisten limits in tests/unit/test_audio_preprocessing.py, tests/unit/test_capture_quality_metadata_contract.py, and tests/unit/test_assistant_runtime.py"
Task: "Add integration coverage for command capture profiles, endpoint padding, and bounded relisten recovery in tests/integration/test_command_capture_endpointing.py and tests/integration/test_gui_runtime_bridge.py"
Task: "Add smoke coverage for clipped-utterance recovery and capture completeness in tests/smoke/test_audio_frontend_quickstart.py and tests/smoke/test_runtime_quickstart.py"
```

## Parallel Example: User Story 2

```bash
Task: "Extend unit coverage for local-first/rescue result shaping, language candidates, and disagreement handling in tests/unit/test_hybrid_command_recognition_contract.py, tests/unit/test_assistant_runtime.py, and tests/unit/test_command_canonicalization.py"
Task: "Add integration coverage for Vosk-first routing, rescue escalation, and recognition-path disagreement handling in tests/integration/test_hybrid_command_recognition.py, tests/integration/test_command_dispatch.py, and tests/integration/test_runtime_offline_behavior.py"
Task: "Add integration coverage for closed-vocabulary filtering, constrained retry, and truthful degraded-mode messages in tests/integration/test_closed_vocabulary_stt.py, tests/integration/test_runtime_modes.py, and tests/integration/test_gui_runtime_bridge.py"
Task: "Add smoke coverage for local-first, rescue, and closed-choice quickstart journeys in tests/smoke/test_audio_frontend_quickstart.py and tests/smoke/test_hybrid_command_recognition_quickstart.py"
```

## Parallel Example: User Story 3

```bash
Task: "Extend unit coverage for qualification-profile selection, enhancement-demotion rules, and field-safe evidence shaping in tests/unit/test_capture_profiles.py, tests/unit/test_assistant_runtime.py, and tests/unit/test_hybrid_command_recognition_contract.py"
Task: "Add integration coverage for simplified-profile behavior, optional-enhancement demotion, and qualification telemetry emission in tests/integration/test_hybrid_command_recognition.py, tests/integration/test_runtime_modes.py, and tests/integration/test_gui_runtime_bridge.py"
Task: "Add smoke coverage for default-vs-simplified qualification runs in tests/smoke/test_audio_frontend_quickstart.py and tests/smoke/test_runtime_quickstart.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate capture completeness and bounded relisten behavior before widening scope

### Incremental Delivery

1. Setup + Foundational establish audio profiles, preprocessing, structured recognition, settings policy, and qualification helpers
2. Deliver US1 for complete-utterance capture and bounded clipped-utterance recovery
3. Deliver US2 for hybrid recognition, bilingual canonicalization, and constrained-mode safety
4. Deliver US3 for Pi 4 qualification, simplified profile support, and metadata-first evidence
5. Finish with Phase 6 polish and the full validation sweep

### Parallel Team Strategy

1. Team aligns on Setup and Foundational together
2. After Phase 2:
   - Developer A: US1 capture profiles, preprocessing, and relisten recovery
   - Developer B: US2 hybrid recognition, dictionary bias, and canonicalization
   - Developer C: US3 qualification profiles, evidence aggregation, and release guidance
3. Rejoin for cross-cutting cleanup and final validation

---

## Notes

- `[P]` tasks are parallel-safe only after their prerequisites are complete
- Every user story includes explicit test tasks because this feature touches STT, runtime safety, settings application, degraded-mode behavior, and observability
- Keep speech meaning runtime-owned; GUI paths must consume the same capture and recognition flow rather than creating a separate interpretation path
- Default telemetry and qualification artifacts must remain metadata-first and must not expose live user audio or raw transcripts
