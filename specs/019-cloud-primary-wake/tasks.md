# Tasks: Cloud-Primary Wake Recognition and Standby Fallback Reliability

**Input**: Design documents from `/specs/019-cloud-primary-wake/`  
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Required because this feature changes runtime standby behavior, STT
provider ordering, wake-policy resolution, canonical wake safety, and
field-safe diagnostics.

**Organization**: Tasks are grouped by user story so each story can be
implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files or test
  slices with no dependency on another incomplete task.
- **[Story]**: User story label for story-specific phases only.
- Every task includes an exact repository path.

## Path Conventions

- **Current project layout**: `main.py`, `controllers/`, `core/`,
  `settings/`, `tts/`, `ui/`, `tests/`, `docs/`
- **Feature focus**: standby wake flow in `core/assistant_runtime.py`,
  wake-capture orchestration in `core/speech/legacy_wake.py`, wake ordering
  and fallback behavior in `core/stt.py`, wake alias scoring in
  `core/wake_word.py`, wake-mode resolution in
  `core/speech/provider_resolver.py`, field-safe diagnostics in
  `core/runtime_diagnostics.py`, and validation under `tests/unit/`,
  `tests/integration/`, and `tests/smoke/`
- **Specification docs**: `specs/019-cloud-primary-wake/contracts/` and
  `specs/019-cloud-primary-wake/quickstart.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare wake fixtures, fake cloud responses, and validation
entry points for Phase 19 work.

- [X] T001 Add Phase 19 fake cloud wake responses, bilingual wake fixtures, and repeated-miss helpers in `tests/conftest.py`
- [X] T002 [P] Create cloud-primary wake unit test scaffolding in `tests/unit/test_cloud_wake_recognition.py`
- [X] T003 [P] Create STT wake integration scaffolding in `tests/integration/test_wake_strategy_modes.py` and `tests/integration/test_google_cloud_stt_runtime.py`
- [X] T004 [P] Add Phase 19 smoke-validation placeholders and evidence sections in `tests/smoke/test_wake_strategy_quickstart.py` and `specs/019-cloud-primary-wake/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared wake contracts, source labels, hint boundaries,
and diagnostics scaffolding required by all user stories.

**CRITICAL**: No user story work should begin until this phase is complete.

- [X] T005 Add failing contract coverage for wake recognition result and standby wake outcome payloads in `tests/unit/test_runtime_contract.py`
- [X] T006 [P] Add failing field-safe diagnostics contract coverage for wake source classification and wake-miss markers in `tests/integration/test_stt_privacy_diagnostics.py`
- [X] T007 [P] Add failing wake phrase-hint and strict wake grammar contract coverage in `tests/unit/test_phrase_hints.py` and `tests/unit/test_strict_vosk_fallback.py`
- [X] T008 [P] Add failing cloud STT wake runtime coverage for `standby_wake` metadata and disabled-rollout parity in `tests/integration/test_google_cloud_stt_runtime.py` and `tests/unit/test_stt_feature_flags.py`
- [X] T009 Extend shared wake source labels, wake statuses, and standby wake outcome fields in `core/command_models.py`
- [X] T010 [P] Add wake-specific hint-cap and strict wake grammar helper boundaries in `core/speech/phrase_hints.py` and `core/stt.py`
- [X] T011 [P] Add field-safe wake diagnostic payload helpers and Phase 19 rollout notes in `core/runtime_diagnostics.py` and `docs/STTInfo.md`

**Checkpoint**: Shared wake contracts and boundaries are ready; user story work
can now begin.

---

## Phase 3: User Story 1 - Wake The Assistant Reliably In Standby (Priority: P1) MVP

**Goal**: Make speech-based standby wake use cloud-primary recognition with
strict local wake fallback while preserving canonical wake acceptance and safe
return to standby.

**Independent Test**: Run wake-phrase fixtures in English, Arabic, and mixed
speech while the assistant is in standby and verify canonical wake acceptance
within the 7-second wake window, including cloud-timeout-to-fallback success
and safe wake-miss return.

### Tests for User Story 1

> **NOTE: Write these tests first and ensure they fail before implementation
> because this story changes constitution-protected runtime and provider
> behavior.**

- [X] T012 [P] [US1] Add unit tests for canonical cloud-primary wake success and cloud-timeout-to-fallback success in `tests/unit/test_cloud_wake_recognition.py`
- [X] T013 [P] [US1] Add unit tests for wake-specific strict fallback match and no-match behavior in `tests/unit/test_strict_vosk_fallback.py`
- [X] T014 [P] [US1] Add integration tests for STT-based standby wake acceptance, wake-miss recovery, and cloud-primary source metadata in `tests/integration/test_wake_strategy_modes.py` and `tests/integration/test_google_cloud_stt_runtime.py`
- [X] T015 [P] [US1] Add smoke coverage for canonical wake and cloud-timeout-to-fallback wake flows in `tests/smoke/test_wake_strategy_quickstart.py`

### Implementation for User Story 1

- [X] T016 [US1] Add cloud-primary wake candidate ordering and strict wake fallback invocation for `usage_mode="standby_wake"` in `core/stt.py`
- [X] T017 [US1] Route `WAKE_MODE_STT_BASED` through structured `standby_wake` capture in `core/speech/legacy_wake.py`
- [X] T018 [US1] Preserve canonical wake gating and safe standby return for accepted or missed speech wake attempts in `core/assistant_runtime.py`
- [X] T019 [US1] Extend wake alias matching and canonical alias reporting for speech wake candidates in `core/wake_word.py` and `core/command_models.py`
- [X] T020 [US1] Run `python -m pytest tests/unit/test_cloud_wake_recognition.py tests/unit/test_strict_vosk_fallback.py tests/integration/test_wake_strategy_modes.py tests/integration/test_google_cloud_stt_runtime.py tests/smoke/test_wake_strategy_quickstart.py -q` and record SC-001, SC-002, and SC-006 evidence in `specs/019-cloud-primary-wake/quickstart.md`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Avoid False Wakes And Unsafe Activations (Priority: P2)

**Goal**: Reject unrelated, command-only, and non-canonical wake-like speech
without accidentally entering active mode, while handling wake-plus-command as
wake-only.

**Independent Test**: Run negative fixtures for noise, unrelated speech,
similar-sounding non-wake words, and wake-plus-command utterances and verify
the assistant rejects or safely constrains them while staying stable.

### Tests for User Story 2

- [X] T021 [P] [US2] Add unit tests for unrelated speech, command-only speech, and similar-sounding non-wake rejection in `tests/unit/test_cloud_wake_recognition.py` and `tests/unit/test_wake_word_profiles.py`
- [X] T022 [P] [US2] Add unit tests for wake-plus-command wake-only handling and approved wake alias boundaries in `tests/unit/test_wake_word_canonical.py` and `tests/unit/test_phrase_hints.py`
- [X] T023 [P] [US2] Add integration tests for non-canonical rejection, `wake_missed` outcomes, and wake-only transitions in `tests/integration/test_wake_strategy_modes.py` and `tests/integration/test_runtime_modes.py`
- [X] T024 [P] [US2] Add field-safe diagnostics tests for `noncanonical_rejected` and `wake_missed` classifications in `tests/integration/test_stt_privacy_diagnostics.py`

### Implementation for User Story 2

- [X] T025 [US2] Build bounded wake hint inventories from approved canonical and curated variants in `core/speech/phrase_hints.py`
- [X] T026 [US2] Enforce strict wake grammar no-match behavior for unrelated or command-only transcripts in `core/stt.py`
- [X] T027 [US2] Treat wake-plus-command utterances as wake-only and drop trailing command text from execution flow in `core/speech/legacy_wake.py` and `core/assistant_runtime.py`
- [X] T028 [US2] Emit `wake_rejected` and `wake_missed` outcomes with non-canonical source classification in `core/assistant_runtime.py` and `core/runtime_diagnostics.py`
- [X] T029 [US2] Run `python -m pytest tests/unit/test_cloud_wake_recognition.py tests/unit/test_wake_word_profiles.py tests/unit/test_wake_word_canonical.py tests/unit/test_phrase_hints.py tests/integration/test_wake_strategy_modes.py tests/integration/test_runtime_modes.py tests/integration/test_stt_privacy_diagnostics.py -q` and record SC-003 plus FR-010 and FR-020 evidence in `specs/019-cloud-primary-wake/quickstart.md`

**Checkpoint**: User Stories 1 and 2 are independently functional and testable.

---

## Phase 5: User Story 3 - Preserve Existing Wake Modes And Standby Stability (Priority: P3)

**Goal**: Keep keyword and hardware-trigger wake behavior intact, maintain
disabled-rollout parity, and ensure repeated wake misses do not destabilize
standby.

**Independent Test**: Validate hardware-trigger wake, low-power keyword wake,
disabled cloud rollout parity, network-down strict local fallback availability,
and at least 50 consecutive wake misses without runtime stall or crash.

### Tests for User Story 3

- [X] T030 [P] [US3] Add unit tests for wake-mode selection during cloud or network loss and strict local fallback availability in `tests/unit/test_provider_resolver.py` and `tests/unit/test_stt_feature_flags.py`
- [X] T031 [P] [US3] Add unit tests for hardware-trigger and keyword wake parity plus repeated wake-miss stability guards in `tests/unit/test_wake_strategy_runtime.py` and `tests/unit/test_assistant_runtime.py`
- [X] T032 [P] [US3] Add integration tests for disabled cloud rollout parity, hardware-trigger wake, keyword wake, and repeated standby misses in `tests/integration/test_runtime_modes.py` and `tests/integration/test_wake_strategy_modes.py`
- [X] T033 [P] [US3] Add smoke coverage for repeated wake misses and non-cloud wake parity in `tests/smoke/test_wake_strategy_quickstart.py`

### Implementation for User Story 3

- [X] T034 [US3] Update STT wake availability resolution so strict local fallback can survive cloud or network failure when permitted in `core/speech/provider_resolver.py`
- [X] T035 [US3] Preserve `keyword_low_power` and `hardware_trigger` wake paths while layering in speech wake ordering in `core/speech/legacy_wake.py` and `core/assistant_runtime.py`
- [X] T036 [US3] Add bounded wake-miss recovery and repeated-miss stability metrics in `core/assistant_runtime.py` and `core/release_metrics.py`
- [X] T037 [US3] Run `python -m pytest tests/unit/test_provider_resolver.py tests/unit/test_stt_feature_flags.py tests/unit/test_wake_strategy_runtime.py tests/unit/test_assistant_runtime.py tests/integration/test_runtime_modes.py tests/integration/test_wake_strategy_modes.py tests/smoke/test_wake_strategy_quickstart.py -q` and record SC-004 plus FR-011, FR-013, and FR-019 evidence in `specs/019-cloud-primary-wake/quickstart.md`

**Checkpoint**: User Stories 1 through 3 are independently functional and testable.

---

## Phase 6: User Story 4 - Provide Field-Safe Wake Telemetry For Debugging (Priority: P4)

**Goal**: Emit structured, field-safe wake telemetry that distinguishes cloud
success, strict fallback usage, non-canonical rejection, and wake-miss cases.

**Independent Test**: Exercise wake accepted, wake rejected, cloud failure plus
fallback success, and cloud-plus-fallback miss paths and verify structured,
field-safe telemetry is emitted for each outcome.

### Tests for User Story 4

- [X] T038 [P] [US4] Add unit tests for source classification, canonical alias reporting, and `wake_missed` outcome payloads in `tests/unit/test_runtime_contract.py`
- [X] T039 [P] [US4] Add integration tests for field-safe accepted, rejected, missed, and fallback-used wake diagnostics in `tests/integration/test_stt_privacy_diagnostics.py` and `tests/integration/test_google_cloud_stt_runtime.py`
- [X] T040 [P] [US4] Add telemetry-pipeline coverage for wake source markers and miss classification in `tests/integration/test_speech_telemetry_pipeline.py`

### Implementation for User Story 4

- [X] T041 [US4] Extend standby wake outcome payloads with source classification, canonical alias, fallback markers, and field-safe flags in `core/command_models.py` and `core/assistant_runtime.py`
- [X] T042 [US4] Emit wake accepted, non-canonical rejected, fallback-used, and `wake_missed` telemetry through `core/runtime_diagnostics.py` and `core/release_metrics.py`
- [X] T043 [US4] Update wake telemetry documentation and validation evidence expectations in `docs/STTInfo.md` and `specs/019-cloud-primary-wake/quickstart.md`
- [X] T044 [US4] Run `python -m pytest tests/unit/test_runtime_contract.py tests/integration/test_stt_privacy_diagnostics.py tests/integration/test_google_cloud_stt_runtime.py tests/integration/test_speech_telemetry_pipeline.py -q` and record SC-005 evidence in `specs/019-cloud-primary-wake/quickstart.md`

**Checkpoint**: All user stories are independently functional and testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Reconcile the shipped behavior with the Phase 19 docs and run the
full validation sweep.

- [X] T045 [P] Reconcile shipped Phase 19 behavior with `specs/019-cloud-primary-wake/contracts/wake-recognition-result-contract.md`, `specs/019-cloud-primary-wake/contracts/strict-wake-fallback-contract.md`, and `specs/019-cloud-primary-wake/contracts/standby-wake-outcome-contract.md`
- [X] T046 [P] Refresh Phase 19 rollout and operator notes in `docs/STTInfo.md` and `docs/implementationPlan.md`
- [X] T047 Run `python -m pytest tests/unit/test_cloud_wake_recognition.py tests/unit/test_strict_vosk_fallback.py tests/unit/test_phrase_hints.py tests/unit/test_wake_word_canonical.py tests/unit/test_wake_word_profiles.py tests/unit/test_provider_resolver.py tests/unit/test_stt_feature_flags.py tests/unit/test_wake_strategy_runtime.py tests/unit/test_assistant_runtime.py tests/unit/test_runtime_contract.py -q` and record results in `specs/019-cloud-primary-wake/quickstart.md`
- [X] T048 Run `python -m pytest tests/integration/test_google_cloud_stt_runtime.py tests/integration/test_wake_strategy_modes.py tests/integration/test_runtime_modes.py tests/integration/test_stt_privacy_diagnostics.py tests/integration/test_speech_telemetry_pipeline.py tests/smoke/test_wake_strategy_quickstart.py -q` and record results in `specs/019-cloud-primary-wake/quickstart.md`
- [X] T049 Run `python -m compileall core tests` and `python -m ruff check .` and record results in `specs/019-cloud-primary-wake/quickstart.md`
- [X] T050 Review `core/stt.py`, `core/assistant_runtime.py`, `core/runtime_diagnostics.py`, `settings/user_profile.json`, and `docs/STTInfo.md` for raw-utterance or credential persistence risks and confirm remaining rollout notes in `specs/019-cloud-primary-wake/tasks.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1: Setup** has no dependencies.
- **Phase 2: Foundational** depends on Setup and blocks all user stories.
- **Phase 3: US1** depends on Foundational and is the MVP.
- **Phase 4: US2** depends on Foundational and validates against the US1
  speech wake path while remaining independently testable with fake wake
  candidates.
- **Phase 5: US3** depends on Foundational and should validate against the
  wake path established in US1.
- **Phase 6: US4** depends on Foundational and should validate after US1 and
  US2 expose the final wake outcome taxonomy.
- **Phase 7: Polish** depends on the selected user stories being complete.

### User Story Dependencies

- **US1 (P1)**: No dependency on other stories after Foundational; delivers the
  cloud-primary wake path MVP.
- **US2 (P2)**: Depends on Foundational; final verification should run after
  US1 because it constrains the speech wake path introduced there.
- **US3 (P3)**: Depends on Foundational; final verification should run after
  US1 because it preserves compatibility around the speech wake path.
- **US4 (P4)**: Depends on Foundational; final verification should run after
  US1 and US2 because it describes their accepted/rejected/missed outcomes.

### Within Each User Story

- Write the listed tests first and confirm they fail before implementation.
- Land shared contract or source-label changes before runtime integration.
- Add diagnostics before marking a story complete.
- Run the story-specific validation command from `quickstart.md` before moving
  to the next checkpoint.

### Parallel Opportunities

- `T002`, `T003`, and `T004` can run in parallel after `T001`.
- `T006`, `T007`, `T008`, `T010`, and `T011` can run in parallel during
  Foundational work.
- `T012`, `T013`, `T014`, and `T015` can run in parallel for US1.
- `T021`, `T022`, `T023`, and `T024` can run in parallel for US2.
- `T030`, `T031`, `T032`, and `T033` can run in parallel for US3.
- `T038`, `T039`, and `T040` can run in parallel for US4.
- `T045` and `T046` can run in parallel during Polish.

---

## Parallel Example: User Story 1

```text
Task: "T012 [P] [US1] Add unit tests for canonical cloud-primary wake success and cloud-timeout-to-fallback success in tests/unit/test_cloud_wake_recognition.py"
Task: "T013 [P] [US1] Add unit tests for wake-specific strict fallback match and no-match behavior in tests/unit/test_strict_vosk_fallback.py"
Task: "T014 [P] [US1] Add integration tests for STT-based standby wake acceptance, wake-miss recovery, and cloud-primary source metadata in tests/integration/test_wake_strategy_modes.py and tests/integration/test_google_cloud_stt_runtime.py"
Task: "T015 [P] [US1] Add smoke coverage for canonical wake and cloud-timeout-to-fallback wake flows in tests/smoke/test_wake_strategy_quickstart.py"
```

## Parallel Example: User Story 2

```text
Task: "T021 [P] [US2] Add unit tests for unrelated speech, command-only speech, and similar-sounding non-wake rejection in tests/unit/test_cloud_wake_recognition.py and tests/unit/test_wake_word_profiles.py"
Task: "T022 [P] [US2] Add unit tests for wake-plus-command wake-only handling and approved wake alias boundaries in tests/unit/test_wake_word_canonical.py and tests/unit/test_phrase_hints.py"
Task: "T023 [P] [US2] Add integration tests for non-canonical rejection, wake_missed outcomes, and wake-only transitions in tests/integration/test_wake_strategy_modes.py and tests/integration/test_runtime_modes.py"
Task: "T024 [P] [US2] Add field-safe diagnostics tests for noncanonical_rejected and wake_missed classifications in tests/integration/test_stt_privacy_diagnostics.py"
```

## Parallel Example: User Story 3

```text
Task: "T030 [P] [US3] Add unit tests for wake-mode selection during cloud or network loss and strict local fallback availability in tests/unit/test_provider_resolver.py and tests/unit/test_stt_feature_flags.py"
Task: "T031 [P] [US3] Add unit tests for hardware-trigger and keyword wake parity plus repeated wake-miss stability guards in tests/unit/test_wake_strategy_runtime.py and tests/unit/test_assistant_runtime.py"
Task: "T032 [P] [US3] Add integration tests for disabled cloud rollout parity, hardware-trigger wake, keyword wake, and repeated standby misses in tests/integration/test_runtime_modes.py and tests/integration/test_wake_strategy_modes.py"
Task: "T033 [P] [US3] Add smoke coverage for repeated wake misses and non-cloud wake parity in tests/smoke/test_wake_strategy_quickstart.py"
```

## Parallel Example: User Story 4

```text
Task: "T038 [P] [US4] Add unit tests for source classification, canonical alias reporting, and wake_missed outcome payloads in tests/unit/test_runtime_contract.py"
Task: "T039 [P] [US4] Add integration tests for field-safe accepted, rejected, missed, and fallback-used wake diagnostics in tests/integration/test_stt_privacy_diagnostics.py and tests/integration/test_google_cloud_stt_runtime.py"
Task: "T040 [P] [US4] Add telemetry-pipeline coverage for wake source markers and miss classification in tests/integration/test_speech_telemetry_pipeline.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup tasks.
2. Complete Phase 2 foundational tasks.
3. Complete Phase 3 User Story 1 tasks.
4. Stop and validate cloud-primary wake plus strict local fallback behavior
   before widening scope.

### Incremental Delivery

1. Deliver US1 for reliable speech wake in standby.
2. Deliver US2 for false-wake rejection and wake-plus-command safety.
3. Deliver US3 for compatibility, degraded behavior, and repeated-miss
   stability.
4. Deliver US4 for field-safe telemetry and release-owner visibility.
5. Finish with Phase 7 reconciliation and full validation.

### Parallel Team Strategy

1. Complete Setup and Foundational work together.
2. After Phase 2:
   - Developer A: US1 wake ordering and structured standby capture
   - Developer B: US2 false-wake controls and wake-plus-command safety
   - Developer C: US3 compatibility, degraded behavior, and repeated-miss stability
   - Developer D: US4 diagnostics and telemetry
3. Rejoin for Phase 7 validation and documentation cleanup.

---

## Notes

- Tests are intentionally first because this feature touches constitution-
  protected runtime, provider, and safety paths.
- Keep cloud-primary wake opt-in and rollback-friendly until the quickstart
  validation passes.
- Do not add broad local dictation or PocketSphinx back into the default wake
  path.
- Do not persist raw utterances or cloud credential material in profile, logs,
  or release artifacts by default.
