# Tasks: Cloud-Primary Command Recognition and Safety-Aware Fallback

**Input**: Design documents from `/specs/018-cloud-command-recognition/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)
**Tests**: Required because this feature touches STT provider behavior, command recognition, runtime orchestration, parser/post-processing safety, protected-command policy, and diagnostics.
**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files or test slices with no dependency on another incomplete task.
- **[Story]**: User story label for story-specific phases only.
- Every task includes an exact repository path.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare shared fixtures, baselines, and validation entry points for command recognition work.

- [X] T001 Create shared fake cloud command recognition helpers plus Arabic, bilingual, and common-command baseline fixtures in `tests/unit/test_cloud_command_recognition.py`
- [X] T002 [P] Create command runtime fixture helpers for protected commands and fallback sessions in `tests/integration/test_command_recognition_runtime.py`
- [X] T003 [P] Add command-recognition source and fallback diagnostic fixture helpers in `tests/integration/test_stt_privacy_diagnostics.py`
- [X] T004 Document the Phase 18 validation commands and expected disabled-rollout baseline in `specs/018-cloud-command-recognition/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared contracts and metadata that all user stories rely on.

**CRITICAL**: No user story implementation should begin until this phase is complete.

- [X] T005 Add contract tests for command recognition result source labels and no-usable-transcript shape in `tests/unit/test_command_recognition_contract.py`
- [X] T006 [P] Add contract tests for command fallback decision trigger/status shapes in `tests/unit/test_command_fallback_decision_contract.py`
- [X] T007 [P] Add contract tests for command safety evaluation policy inputs in `tests/unit/test_command_safety_evaluation_contract.py`
- [X] T008 Extend allowed command recognition source labels for `rescue_strict_vosk` and `cloud_unavailable` in `core/command_models.py`
- [X] T009 Add or update command fallback decision metadata helpers in `core/command_models.py`
- [X] T010 Ensure recognition configuration snapshots expose command-safe rollout state without credential or raw-content fields in `core/command_models.py`
- [X] T011 Add field-safe command recognition diagnostic assertions in `tests/integration/test_stt_privacy_diagnostics.py`
- [X] T012 Update command recognition behavior notes for Phase 18 scope in `docs/STTInfo.md`

**Checkpoint**: Foundation ready; user story implementation can now begin in priority order or in parallel by separate owners.

---

## Phase 3: User Story 1 - Understand Commands With Cloud-Primary Recognition (Priority: P1) MVP

**Goal**: Command-mode recognition uses the cloud recognizer first when explicitly enabled and available, preserving transcript, alternatives, confidence, selected/detected language, and existing command flow compatibility.

**Independent Test**: Enable cloud-primary recognition with fake cloud candidates, run command-mode recognition for supported English, Arabic, and bilingual commands, and verify `CommandRecognitionResult` contains cloud-primary source metadata without bypassing runtime policy.

### Tests for User Story 1

- [X] T013 [P] [US1] Add unit tests for cloud-primary command candidate ordering, alternatives, and Arabic/bilingual resolution baseline comparison in `tests/unit/test_cloud_command_recognition.py`
- [X] T014 [P] [US1] Add unit tests for disabled cloud rollout preserving local command candidate ordering in `tests/unit/test_stt_feature_flags.py`
- [X] T015 [P] [US1] Add adapter compatibility tests for cloud-primary metadata preservation in `tests/unit/test_provider_registry.py`
- [X] T016 [P] [US1] Add integration tests for `VoiceListener.listen_command_result` cloud-primary command metadata in `tests/integration/test_command_recognition_runtime.py`

### Implementation for User Story 1

- [X] T017 [US1] Update command-mode candidate ordering to prefer cloud primary only when enabled in `core/stt.py`
- [X] T018 [US1] Preserve cloud alternatives, confidence, selected language, detected language, latency, and source metadata in `core/stt.py`
- [X] T019 [US1] Ensure cloud command candidates adapt into `CommandRecognitionResult` without changing public listener method signatures in `core/stt.py`
- [X] T020 [US1] Preserve existing runtime post-processing, parser, confidence, dispatcher, and resolver flow for cloud candidates in `core/assistant_runtime.py`
- [X] T021 [US1] Emit field-safe cloud command source and latency diagnostics for successful command candidates in `core/stt.py`
- [X] T022 [US1] Run the User Story 1 validation commands and record cloud-primary versus local-first Arabic/bilingual success counts in `specs/018-cloud-command-recognition/quickstart.md`

**Checkpoint**: MVP complete; cloud-primary command recognition is independently testable while disabled rollout remains compatible.

---

## Phase 4: User Story 2 - Recover Safely Through Strict Command Fallback (Priority: P2)

**Goal**: Cloud failures, low-confidence outcomes, language mismatch, parser rejection, and no-match fallback cases recover through strict command grammar or existing retry/confirmation/refusal without broad dictation.

**Independent Test**: Simulate cloud timeout, empty result, unavailable state, low confidence, language mismatch, parser rejection, strict fallback match, and strict fallback no-match; verify strict fallback is bounded and no unsupported transcript is promoted.

### Tests for User Story 2

- [X] T023 [P] [US2] Add unit tests for cloud timeout, empty result, unavailable state, and strict fallback trigger behavior in `tests/unit/test_strict_vosk_fallback.py`
- [X] T024 [P] [US2] Add unit tests for strict fallback disabled returning no usable command transcript in `tests/unit/test_stt_feature_flags.py`
- [X] T025 [P] [US2] Add integration tests for runtime rescue after low confidence, language mismatch, parser rejection, and fallback-to-retry baseline comparison in `tests/integration/test_command_recognition_runtime.py`
- [X] T026 [P] [US2] Add diagnostics tests for fallback decisions and failure reason codes in `tests/integration/test_stt_privacy_diagnostics.py`

### Implementation for User Story 2

- [X] T027 [US2] Route provider-level cloud failures to strict command fallback when enabled and to no usable transcript when disabled in `core/stt.py`
- [X] T028 [US2] Ensure strict fallback only uses approved command inventory or active closed vocabulary phrases in `core/stt.py`
- [X] T029 [US2] Prevent broad Vosk dictation and default PocketSphinx command candidates after cloud failure in `core/stt.py`
- [X] T030 [US2] Route runtime-level low confidence, language mismatch, alternatives conflict, endpoint quality, and parser rejection to existing rescue or recovery policy in `core/assistant_runtime.py`
- [X] T031 [US2] Emit strict fallback matched, no-match, unavailable, and failure diagnostics without raw utterance persistence in `core/stt.py`
- [X] T032 [US2] Run the User Story 2 validation commands and record cloud-primary versus local-first fallback-to-retry counts in `specs/018-cloud-command-recognition/quickstart.md`

**Checkpoint**: Safe recovery complete; cloud failure and strict fallback scenarios are independently testable.

---

## Phase 5: User Story 3 - Use Command Hints That Reflect Assistive Use (Priority: P3)

**Goal**: Command phrase hints include approved assistive commands, Arabic variants, English variants, bilingual/phonetic forms, and deterministic capped ordering without raw user utterances.

**Independent Test**: Generate command phrase hints repeatedly and verify deterministic ordering, deduplication, required command families, Arabic/bilingual/phonetic variants, cap behavior, and no raw user-derived phrases.

### Tests for User Story 3

- [X] T033 [P] [US3] Add exact-output tests for deterministic command hint ordering and deduplication in `tests/unit/test_phrase_hints.py`
- [X] T034 [P] [US3] Add tests for required assistive command families and protected command priority in `tests/unit/test_phrase_hints.py`
- [X] T035 [P] [US3] Add tests for Arabic, bilingual, phonetic, and common STT mistake command variants in `tests/unit/test_phrase_hints.py`
- [X] T036 [P] [US3] Add tests for cloud hint cap and strict grammar cap behavior in `tests/unit/test_phrase_hints.py`

### Implementation for User Story 3

- [X] T037 [US3] Add curated assistive command, Arabic, bilingual, phonetic, and STT mistake variants in `core/speech/phrase_hints.py`
- [X] T038 [US3] Add stable command hint priority ordering and maximum-size enforcement in `core/speech/phrase_hints.py`
- [X] T039 [US3] Ensure cloud command hint selection uses the capped command hint inventory in `core/stt.py`
- [X] T040 [US3] Ensure strict command fallback grammar uses approved capped command inventory without raw user utterance history in `core/stt.py`
- [X] T041 [US3] Document command phrase hint sources, caps, and rollout expectations in `docs/STTInfo.md`
- [X] T042 [US3] Run the User Story 3 validation commands and record results in `specs/018-cloud-command-recognition/quickstart.md`

**Checkpoint**: Hint governance complete; cloud and strict fallback hints are deterministic, bounded, and auditable.

---

## Phase 6: User Story 4 - Preserve Safety for Protected Commands (Priority: P4)

**Goal**: Cloud-primary and strict fallback candidates feed the existing confidence and confirmation policies so protected, ambiguous, and wake-plus-command phrases remain safe.

**Independent Test**: Exercise protected high-confidence commands, medium-risk conflicting alternatives, low-risk high-confidence commands, parser rejection, fallback candidates, and wake-plus-protected-command phrases; verify decisions match existing safety policy.

### Tests for User Story 4

- [X] T043 [P] [US4] Add unit tests for protected high-confidence cloud commands requiring confirmation in `tests/unit/test_command_confidence_policy.py`
- [X] T044 [P] [US4] Add unit tests for medium-risk conflicting alternatives confirming or retrying in `tests/unit/test_command_confidence_policy.py`
- [X] T045 [P] [US4] Add unit tests for wake-plus-command normalization and safety penalties in `tests/unit/test_command_post_processing.py`
- [X] T046 [P] [US4] Add integration tests for protected cloud and strict fallback commands in `tests/integration/test_command_recognition_runtime.py`

### Implementation for User Story 4

- [X] T047 [US4] Preserve protected command confirmation requirements for cloud and strict fallback candidates in `core/assistant_runtime.py`
- [X] T048 [US4] Penalize or normalize wake wording during command-mode post-processing without treating it as confirmation in `core/command_post_processing.py`
- [X] T049 [US4] Ensure parser rejection and no command-like shapes cannot execute raw cloud or fallback text in `core/assistant_runtime.py`
- [X] T050 [US4] Preserve low-risk high-confidence direct execution only after clean parser acceptance in `core/assistant_runtime.py`
- [X] T051 [US4] Emit confidence band, alternatives conflict, protected-command, and wake-plus-command safety diagnostics in `core/assistant_runtime.py`
- [X] T052 [US4] Run the User Story 4 validation commands and record results in `specs/018-cloud-command-recognition/quickstart.md`

**Checkpoint**: Safety complete; protected and ambiguous command paths remain governed by existing runtime policy.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validate the full feature, update documentation, and clean up cross-story integration risks.

- [X] T053 [P] Update Phase 18 behavior, configuration, diagnostics, and fallback documentation in `docs/STTInfo.md`
- [X] T054 [P] Update release or diagnostics notes for command recognition source/fallback events in `docs/implementationPlan.md`
- [X] T055 Run `python -m pytest tests/unit/test_cloud_command_recognition.py tests/unit/test_stt_feature_flags.py tests/unit/test_strict_vosk_fallback.py tests/unit/test_phrase_hints.py tests/unit/test_command_confidence_policy.py tests/unit/test_command_post_processing.py -q` and record unit baseline comparison results in `specs/018-cloud-command-recognition/quickstart.md`
- [X] T056 Run `python -m pytest tests/integration/test_command_recognition_runtime.py tests/integration/test_stt_privacy_diagnostics.py -q` and record integration baseline comparison results in `specs/018-cloud-command-recognition/quickstart.md`
- [X] T057 Run `python -m compileall core tests` and record results in `specs/018-cloud-command-recognition/quickstart.md`
- [X] T058 Run `python -m ruff check .` and record results in `specs/018-cloud-command-recognition/quickstart.md`
- [X] T059 Review all Phase 18 source changes for no raw utterance or credential persistence in `core/`
- [X] T060 Confirm final task completion and remaining rollout notes in `specs/018-cloud-command-recognition/tasks.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1: Setup** has no dependencies.
- **Phase 2: Foundational** depends on Setup and blocks all user stories.
- **Phase 3: US1** depends on Foundational and is the MVP.
- **Phase 4: US2** depends on Foundational and can proceed after or alongside US1 once shared metadata exists.
- **Phase 5: US3** depends on Foundational and can proceed alongside US1/US2 because it mainly touches hint generation.
- **Phase 6: US4** depends on Foundational and should validate against US1/US2 candidates before final integration.
- **Phase 7: Polish** depends on the selected user stories being complete.

### User Story Dependencies

- **US1 (P1)**: No dependency on other stories after Foundational; delivers cloud-primary command candidate MVP.
- **US2 (P2)**: Depends on Foundational; integrates with US1 for cloud failure paths but remains independently testable with fake failures.
- **US3 (P3)**: Depends on Foundational; provides bounded command hint quality and can run in parallel with US1/US2.
- **US4 (P4)**: Depends on Foundational; safety tests can start early but final validation should run after US1 and US2 candidate paths exist.

### Within Each User Story

- Write failing tests first.
- Update shared contracts before runtime behavior.
- Implement listener/provider ordering before runtime integration.
- Add diagnostics before declaring the story complete.
- Run the story-specific validation from `quickstart.md` before moving to the next checkpoint.

---

## Parallel Opportunities

- Setup tasks T002 and T003 can run in parallel.
- Foundational contract tests T006 and T007 can run in parallel.
- US1 test tasks T013 through T016 can run in parallel.
- US2 test tasks T023 through T026 can run in parallel.
- US3 test tasks T033 through T036 can run in parallel.
- US4 test tasks T043 through T046 can run in parallel.
- Documentation tasks T053 and T054 can run in parallel after implementation behavior stabilizes.

---

## Parallel Example: User Story 1

```text
Task: "T013 [P] [US1] Add unit tests for cloud-primary command candidate ordering, alternatives, and Arabic/bilingual resolution baseline comparison in tests/unit/test_cloud_command_recognition.py"
Task: "T014 [P] [US1] Add unit tests for disabled cloud rollout preserving local command candidate ordering in tests/unit/test_stt_feature_flags.py"
Task: "T015 [P] [US1] Add adapter compatibility tests for cloud-primary metadata preservation in tests/unit/test_provider_registry.py"
Task: "T016 [P] [US1] Add integration tests for VoiceListener.listen_command_result cloud-primary command metadata in tests/integration/test_command_recognition_runtime.py"
```

## Parallel Example: User Story 2

```text
Task: "T023 [P] [US2] Add unit tests for cloud timeout, empty result, unavailable state, and strict fallback trigger behavior in tests/unit/test_strict_vosk_fallback.py"
Task: "T024 [P] [US2] Add unit tests for strict fallback disabled returning no usable command transcript in tests/unit/test_stt_feature_flags.py"
Task: "T025 [P] [US2] Add integration tests for runtime rescue after low confidence, language mismatch, parser rejection, and fallback-to-retry baseline comparison in tests/integration/test_command_recognition_runtime.py"
Task: "T026 [P] [US2] Add diagnostics tests for fallback decisions and failure reason codes in tests/integration/test_stt_privacy_diagnostics.py"
```

## Parallel Example: User Story 3

```text
Task: "T033 [P] [US3] Add exact-output tests for deterministic command hint ordering and deduplication in tests/unit/test_phrase_hints.py"
Task: "T034 [P] [US3] Add tests for required assistive command families and protected command priority in tests/unit/test_phrase_hints.py"
Task: "T035 [P] [US3] Add tests for Arabic, bilingual, phonetic, and common STT mistake command variants in tests/unit/test_phrase_hints.py"
Task: "T036 [P] [US3] Add tests for cloud hint cap and strict grammar cap behavior in tests/unit/test_phrase_hints.py"
```

## Parallel Example: User Story 4

```text
Task: "T043 [P] [US4] Add unit tests for protected high-confidence cloud commands requiring confirmation in tests/unit/test_command_confidence_policy.py"
Task: "T044 [P] [US4] Add unit tests for medium-risk conflicting alternatives confirming or retrying in tests/unit/test_command_confidence_policy.py"
Task: "T045 [P] [US4] Add unit tests for wake-plus-command normalization and safety penalties in tests/unit/test_command_post_processing.py"
Task: "T046 [P] [US4] Add integration tests for protected cloud and strict fallback commands in tests/integration/test_command_recognition_runtime.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup tasks.
2. Complete Phase 2 foundational contract and metadata tasks.
3. Complete Phase 3 User Story 1 tasks.
4. Stop and validate cloud-primary command candidate behavior with disabled-rollout parity.

### Incremental Delivery

1. Deliver US1 for cloud-primary command candidates.
2. Deliver US2 for strict fallback and safe recovery.
3. Deliver US3 for command hint quality and bounded inventories.
4. Deliver US4 for protected-command and wake-plus-command safety.
5. Run Phase 7 validation before implementation is considered complete.

### Parallel Team Strategy

1. Complete Setup and Foundational tasks together.
2. Assign US1 and US2 to runtime/STT owners.
3. Assign US3 to phrase-hint/test owner.
4. Assign US4 to runtime safety/post-processing owner.
5. Integrate at checkpoints using `quickstart.md` validation.

## Notes

- Tests are intentionally first because this feature touches constitution-protected runtime and safety paths.
- Keep cloud behavior opt-in and rollback-friendly until all quickstart validation passes.
- Do not add broad local dictation or PocketSphinx to the default command path.
- Do not persist raw utterances or cloud credential material in profile, logs, or release artifacts by default.
