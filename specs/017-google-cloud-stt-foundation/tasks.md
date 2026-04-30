# Tasks: Google Cloud STT Foundation and Strict Fallback Contracts

**Input**: Design documents from `/specs/017-google-cloud-stt-foundation/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are REQUIRED because this feature changes provider adapters,
STT candidate ordering, runtime-facing recognition metadata, fallback safety,
settings/environment controls, and field-safe diagnostics.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this belongs to (e.g. `US1`, `US2`, `US3`)
- Include exact file paths in descriptions

## Path Conventions

- **Current project layout**: `main.py`, `controllers/`, `core/`, `settings/`, `tts/`, `ui/`, `tests/`, `docs/`
- **Feature focus**: Google Cloud STT boundary in `core/speech/google_cloud_stt.py`; deterministic hints in `core/speech/phrase_hints.py`; candidate ordering, strict Vosk fallback, and PocketSphinx gating in `core/stt.py`; provider contracts in `core/speech/interfaces.py`, `core/speech/legacy_stt.py`, and `core/speech/provider_registry.py`; structured metadata in `core/command_models.py`; documentation in `docs/STTInfo.md`; validation under `tests/unit/` and `tests/integration/`
- **Specification docs**: `specs/017-google-cloud-stt-foundation/contracts/` and `specs/017-google-cloud-stt-foundation/quickstart.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare optional cloud dependency, test entry points, and documentation surfaces without changing runtime behavior.

- [X] T001 Add the optional `google-cloud-speech` dependency entry to `requirements.txt` and credential/setup guidance to `docs/STTInfo.md`
- [X] T002 [P] Create cloud STT unit test scaffolding in `tests/unit/test_google_cloud_stt.py`
- [X] T003 [P] Create phrase-hint and strict-fallback unit test scaffolding in `tests/unit/test_phrase_hints.py` and `tests/unit/test_strict_vosk_fallback.py`
- [X] T004 [P] Create feature-flag, provider, and runtime integration test scaffolding in `tests/unit/test_stt_feature_flags.py`, `tests/unit/test_provider_registry.py`, `tests/integration/test_google_cloud_stt_runtime.py`, and `tests/integration/test_stt_privacy_diagnostics.py`
- [X] T005 [P] Add Phase 17 validation evidence sections to `specs/017-google-cloud-stt-foundation/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define shared contracts, configuration resolution, and safe defaults that every user story depends on.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T006 Add failing tests for default disabled cloud primary, disabled strict Vosk fallback, disabled PocketSphinx compatibility, timeout defaults, and max alternatives in `tests/unit/test_stt_feature_flags.py`
- [X] T007 [P] Add failing tests for cloud candidate, provider availability, failure reason, language metadata, and diagnostic model validation in `tests/unit/test_google_cloud_stt.py` and `tests/unit/test_provider_registry.py`
- [X] T008 [P] Add failing tests for no-credential provider startup and unchanged public listener methods in `tests/integration/test_google_cloud_stt_runtime.py`
- [X] T009 Define Phase 17 recognition constants, failure reason codes, source labels, configuration snapshot fields, and metadata helpers in `core/command_models.py`
- [X] T010 Add environment-driven STT configuration resolution for `EGB_STT_CLOUD_PRIMARY_ENABLED`, `EGB_STT_STRICT_VOSK_FALLBACK_ENABLED`, `EGB_STT_ENABLE_SPHINX_COMPAT`, `EGB_STT_CLOUD_TIMEOUT_S`, and `EGB_STT_CLOUD_MAX_ALTERNATIVES` in `core/stt.py`
- [X] T011 [P] Create optional-import Google Cloud STT module skeleton with no-credential availability checks in `core/speech/google_cloud_stt.py`
- [X] T012 [P] Create deterministic phrase-hints module skeleton with mode constants and field-safe output metadata in `core/speech/phrase_hints.py`
- [X] T013 Update provider-facing speech interfaces and metadata accessors for cloud source, `ProviderAvailabilityState`, availability, and structured recognition support in `core/speech/interfaces.py` and `core/speech/provider_registry.py`
- [X] T014 Preserve legacy adapter compatibility for `listen_any`, `listen_command`, `listen_command_result`, and `listen_command_window` while passing through Phase 17 recognition metadata in `core/speech/legacy_stt.py`

**Checkpoint**: Shared contracts, feature flags, optional imports, and provider metadata are ready; user story work can begin.

---

## Phase 3: User Story 1 - Use Cloud-Grade Recognition When Available (Priority: P1) MVP

**Goal**: Let explicitly enabled cloud-primary recognition return structured candidates with alternatives, confidence, language metadata, and provider source without changing the public command flow.

**Independent Test**: Enable cloud-primary recognition with a fake available client, submit representative short command audio, and verify a structured cloud candidate reaches `CommandRecognitionResult` while public listener methods remain compatible.

### Tests for User Story 1

> **NOTE: Write these tests FIRST and ensure they fail before implementation**
> because this story changes provider adapter behavior and runtime-facing STT metadata.

- [X] T015 [P] [US1] Add fake successful Google client response tests for transcript, alternatives, confidence, selected language, detected language, and latency in `tests/unit/test_google_cloud_stt.py`
- [X] T016 [P] [US1] Add cloud-primary command integration tests that verify `VoiceListener.listen_command_result()` emits `cloud_primary` metadata without changing public method signatures in `tests/integration/test_google_cloud_stt_runtime.py`
- [X] T017 [P] [US1] Add adapter compatibility tests for cloud candidate propagation through `LegacySpeechToTextAdapter.listen_command_result()` in `tests/unit/test_provider_registry.py`

### Implementation for User Story 1

- [X] T018 [US1] Implement Google client creation, short-utterance recognition request construction, timeout parameter use, and fake-client injection in `core/speech/google_cloud_stt.py`
- [X] T019 [US1] Implement cloud response parsing into structured candidates with primary transcript, alternative transcripts, confidence, selected language, detected language, source, and latency in `core/speech/google_cloud_stt.py`
- [X] T020 [US1] Integrate cloud-primary candidate collection into `_recognize_audio_candidates()` behind `EGB_STT_CLOUD_PRIMARY_ENABLED` in `core/stt.py`
- [X] T021 [US1] Map successful cloud candidates into existing `CommandRecognitionResult` fields without changing public listener method names in `core/stt.py` and `core/command_models.py`
- [X] T022 [US1] Emit field-safe cloud recognition source diagnostics for successful cloud-primary decisions in `core/stt.py`
- [X] T023 [US1] Run US1 validation (`python -m pytest tests/unit/test_google_cloud_stt.py tests/unit/test_provider_registry.py tests/integration/test_google_cloud_stt_runtime.py -q`) and record `SC-001` and `SC-008` evidence in `specs/017-google-cloud-stt-foundation/quickstart.md`

**Checkpoint**: User Story 1 is independently functional and testable as the MVP.

---

## Phase 4: User Story 2 - Fail Safely When Cloud Recognition Cannot Be Used (Priority: P2)

**Goal**: Classify missing credentials, timeout, auth, quota, service, empty-result, and unknown cloud failures into stable reason codes and recover safely without crashing or guessing.

**Independent Test**: Exercise each fake cloud failure and verify the stable reason code, bounded timeout/retry behavior, no-credential startup, and no usable transcript when strict Vosk fallback is disabled.

### Tests for User Story 2

- [X] T024 [P] [US2] Add unit tests for all required cloud failure reason codes and exception mappings in `tests/unit/test_google_cloud_stt.py`
- [X] T025 [P] [US2] Add timeout and one-transient-retry tests for the 3-second default cloud attempt bound in `tests/unit/test_google_cloud_stt.py`
- [X] T026 [P] [US2] Add no-credential startup and cloud-failure recovery integration tests in `tests/integration/test_google_cloud_stt_runtime.py`
- [X] T027 [P] [US2] Add privacy diagnostics tests proving credentials and raw utterances are absent from profile/log/artifact payloads by default in `tests/integration/test_stt_privacy_diagnostics.py`

### Implementation for User Story 2

- [X] T028 [US2] Implement credential missing detection and no-request availability behavior in `core/speech/google_cloud_stt.py`
- [X] T029 [US2] Implement cloud exception classification for `cloud_network_timeout`, `cloud_auth_error`, `cloud_quota_error`, `cloud_service_unavailable`, `cloud_empty_result`, and `cloud_unknown_failure` in `core/speech/google_cloud_stt.py`
- [X] T030 [US2] Implement bounded timeout and at most one transient retry inside the existing listen window in `core/speech/google_cloud_stt.py` and `core/stt.py`
- [X] T031 [US2] Ensure cloud failure with strict Vosk fallback disabled returns no usable transcript and delegates to existing recovery instead of PocketSphinx or unrestricted local recognition in `core/stt.py`
- [X] T032 [US2] Emit field-safe failure diagnostics with reason code, latency category, fallback decision, and no raw utterance or credential material in `core/stt.py`, `core/release_artifacts.py`, and `core/release_models.py`
- [X] T033 [US2] Run US2 validation (`python -m pytest tests/unit/test_google_cloud_stt.py tests/integration/test_google_cloud_stt_runtime.py tests/integration/test_stt_privacy_diagnostics.py -q`) and record `SC-002`, `SC-003`, `SC-007`, and `SC-009` evidence in `specs/017-google-cloud-stt-foundation/quickstart.md`

**Checkpoint**: User Stories 1 and 2 are independently functional and safe under cloud-unavailable conditions.

---

## Phase 5: User Story 3 - Constrain Local Fallbacks to Safe Vocabularies (Priority: P3)

**Goal**: Convert Vosk fallback into strict wake, command, confirmation, and closed-choice decoding so unsupported speech returns no usable transcript instead of arbitrary command text.

**Independent Test**: Enable strict Vosk fallback and exercise wake, command, confirmation, and closed-choice modes with valid phrases, near misses, unrelated speech, and silence, then verify only grammar-approved matches become usable transcripts.

### Tests for User Story 3

- [X] T034 [P] [US3] Add strict Vosk fallback unit tests for `wake_grammar`, `command_inventory`, `closed_choice`, no-match, unavailable Vosk, and confidence handling in `tests/unit/test_strict_vosk_fallback.py`
- [X] T035 [P] [US3] Add command recognition integration tests proving command mode rejects arbitrary Vosk free-form text and respects closed vocabulary choices in `tests/integration/test_command_recognition_runtime.py`
- [X] T036 [P] [US3] Add fallback ordering tests proving cloud failure proceeds to strict Vosk only when `EGB_STT_STRICT_VOSK_FALLBACK_ENABLED=1` in `tests/integration/test_google_cloud_stt_runtime.py`

### Implementation for User Story 3

- [X] T037 [US3] Implement strict Vosk fallback mode selection and grammar payload construction for `wake_grammar`, `command_inventory`, and `closed_choice` in `core/stt.py`
- [X] T038 [US3] Validate Vosk matches against active grammar phrases and return no usable transcript for no-match outcomes in `core/stt.py`
- [X] T039 [US3] Wire closed-vocabulary choices and confirmation/onboarding contexts into strict fallback grammar construction in `core/stt.py` and `core/closed_vocabulary.py`
- [X] T040 [US3] Map strict fallback outcomes into `CommandRecognitionResult` metadata without exposing arbitrary text for no-match outcomes in `core/stt.py` and `core/command_models.py`
- [X] T041 [US3] Emit strict fallback diagnostics for matched, no-match, unavailable, and failed Vosk outcomes in `core/stt.py`
- [X] T042 [US3] Run US3 validation (`python -m pytest tests/unit/test_strict_vosk_fallback.py tests/integration/test_command_recognition_runtime.py tests/integration/test_google_cloud_stt_runtime.py -q`) and record `SC-004` evidence in `specs/017-google-cloud-stt-foundation/quickstart.md`

**Checkpoint**: User Stories 1, 2, and 3 are independently functional and safe across cloud and local fallback paths.

---

## Phase 6: User Story 4 - Keep Recognition Hints Deterministic and Rollback-Friendly (Priority: P4)

**Goal**: Generate deterministic mode-specific phrase hints, keep PocketSphinx out of default accuracy decisions, expose rollback controls, and document field-safe diagnostics.

**Independent Test**: Generate wake, command, confirmation, and onboarding hints twice, verify exact outputs and variants, confirm PocketSphinx contributes zero default candidates unless compatibility is enabled, and verify rollback controls preserve existing runtime flow.

### Tests for User Story 4

- [X] T043 [P] [US4] Add exact-output tests for wake, command, confirmation, and onboarding phrase hints in `tests/unit/test_phrase_hints.py`
- [X] T044 [P] [US4] Add tests for English, Arabic, bilingual, phonetic, common STT-mistake, assistive phrase, and safety-critical variants in `tests/unit/test_phrase_hints.py`
- [X] T045 [P] [US4] Add PocketSphinx compatibility gate tests proving zero default Sphinx candidates and explicit debug-only enablement in `tests/unit/test_stt_feature_flags.py` and `tests/integration/test_command_recognition_runtime.py`
- [X] T046 [P] [US4] Add provider metadata and rollback configuration tests for cloud disabled, strict Vosk disabled, and safe existing-runtime behavior in `tests/unit/test_provider_registry.py` and `tests/integration/test_google_cloud_stt_runtime.py`

### Implementation for User Story 4

- [X] T047 [US4] Implement deterministic phrase hint generation from `core.parser.COMMAND_CATALOG`, `core.closed_vocabulary`, wake aliases, assistive phrases, and safety-critical commands in `core/speech/phrase_hints.py`
- [X] T048 [US4] Add English, Arabic, bilingual, phonetic, and common STT-mistake variants with stable ordering and deduplication in `core/speech/phrase_hints.py`
- [X] T049 [US4] Integrate phrase hints into cloud recognition requests and strict Vosk grammar construction in `core/speech/google_cloud_stt.py` and `core/stt.py`
- [X] T050 [US4] Gate PocketSphinx candidate generation behind `EGB_STT_ENABLE_SPHINX_COMPAT=1` and remove it from default wake and command ranking in `core/stt.py`
- [X] T051 [US4] Update provider metadata and runtime configuration diagnostics to expose effective cloud, strict Vosk, Sphinx compatibility, timeout, and max-alternative controls in `core/speech/provider_registry.py` and `core/stt.py`
- [X] T052 [US4] Update operator documentation for Google Cloud dependency, credentials, feature flags, fallback order, PocketSphinx compatibility, and rollback behavior in `docs/STTInfo.md`
- [X] T053 [US4] Run US4 validation (`python -m pytest tests/unit/test_phrase_hints.py tests/unit/test_stt_feature_flags.py tests/unit/test_provider_registry.py tests/integration/test_command_recognition_runtime.py tests/integration/test_google_cloud_stt_runtime.py -q`) and record `SC-005` and `SC-006` evidence in `specs/017-google-cloud-stt-foundation/quickstart.md`

**Checkpoint**: All user stories are independently functional and validation-ready.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final contract alignment, cleanup, documentation completeness, and full validation across all stories.

- [X] T054 [P] Refresh Phase 17 contracts to match shipped candidate, phrase hint, strict fallback, and recognition configuration payloads in `specs/017-google-cloud-stt-foundation/contracts/cloud-stt-candidate-contract.md`, `specs/017-google-cloud-stt-foundation/contracts/phrase-hints-contract.md`, `specs/017-google-cloud-stt-foundation/contracts/strict-vosk-fallback-contract.md`, and `specs/017-google-cloud-stt-foundation/contracts/recognition-configuration-contract.md`
- [X] T055 Remove stale `speech_recognition.recognize_google()` and default PocketSphinx accuracy-path assumptions from `core/stt.py` and `docs/STTInfo.md`
- [X] T056 [P] Add regression tests covering public listener compatibility, cloud disabled defaults, strict fallback disabled recovery, detected-language metadata, and field-safe diagnostics in `tests/unit/test_google_cloud_stt.py`, `tests/unit/test_stt_feature_flags.py`, and `tests/integration/test_stt_privacy_diagnostics.py`
- [X] T057 Run the full validation sweep from `specs/017-google-cloud-stt-foundation/quickstart.md` (`python -m pytest tests/unit/test_google_cloud_stt.py tests/unit/test_phrase_hints.py tests/unit/test_strict_vosk_fallback.py tests/unit/test_stt_feature_flags.py tests/unit/test_provider_registry.py -q`; `python -m pytest tests/integration/test_google_cloud_stt_runtime.py tests/integration/test_command_recognition_runtime.py tests/integration/test_stt_privacy_diagnostics.py -q`; `python -m compileall core tests`; `python -m ruff check .`) and record outputs in `specs/017-google-cloud-stt-foundation/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion and is the MVP
- **User Story 2 (Phase 4)**: Depends on Foundational completion and can be implemented after or alongside US1 cloud adapter work, but should validate failure handling before wider rollout
- **User Story 3 (Phase 5)**: Depends on Foundational completion and benefits from US2 failure classification so fallback transitions are testable end-to-end
- **User Story 4 (Phase 6)**: Depends on Foundational completion and can progress in parallel where it only touches phrase hints, docs, and compatibility gating; final integration should follow US1 and US3
- **Polish (Phase 7)**: Depends on completion of the user stories selected for release scope

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on other stories
- **US2 (P2)**: Starts after Foundational; uses the cloud adapter boundary from US1 for full integration but its failure-classification tests can be developed independently
- **US3 (P3)**: Starts after Foundational; strict Vosk fallback can be developed independently with fake recognizer payloads and then integrated with US2 fallback decisions
- **US4 (P4)**: Starts after Foundational; phrase-hint generation and Sphinx gating are independently testable, with final integration into US1/US3 paths

### Within Each User Story

- Write the listed tests first and confirm they fail before implementation
- Implement contract/data-model structures before provider-specific wiring
- Land provider or fallback behavior before diagnostics and quickstart evidence
- Run the listed validation command and update `specs/017-google-cloud-stt-foundation/quickstart.md` before marking the story complete

### Parallel Opportunities

- `T002`, `T003`, `T004`, and `T005` can run in parallel after `T001`
- `T007`, `T008`, `T011`, and `T012` can run in parallel after `T006`
- `T015`, `T016`, and `T017` can run in parallel for US1
- `T024`, `T025`, `T026`, and `T027` can run in parallel for US2
- `T034`, `T035`, and `T036` can run in parallel for US3
- `T043`, `T044`, `T045`, and `T046` can run in parallel for US4
- `T054` and `T056` can run in parallel during Polish

---

## Parallel Example: User Story 1

```bash
Task: "Add fake successful Google client response tests for transcript, alternatives, confidence, selected language, detected language, and latency in tests/unit/test_google_cloud_stt.py"
Task: "Add cloud-primary command integration tests that verify VoiceListener.listen_command_result() emits cloud_primary metadata without changing public method signatures in tests/integration/test_google_cloud_stt_runtime.py"
Task: "Add adapter compatibility tests for cloud candidate propagation through LegacySpeechToTextAdapter.listen_command_result() in tests/unit/test_provider_registry.py"
```

## Parallel Example: User Story 2

```bash
Task: "Add unit tests for all required cloud failure reason codes and exception mappings in tests/unit/test_google_cloud_stt.py"
Task: "Add timeout and one-transient-retry tests for the 3-second default cloud attempt bound in tests/unit/test_google_cloud_stt.py"
Task: "Add no-credential startup and cloud-failure recovery integration tests in tests/integration/test_google_cloud_stt_runtime.py"
Task: "Add privacy diagnostics tests proving credentials and raw utterances are absent from profile/log/artifact payloads by default in tests/integration/test_stt_privacy_diagnostics.py"
```

## Parallel Example: User Story 3

```bash
Task: "Add strict Vosk fallback unit tests for wake_grammar, command_inventory, closed_choice, no-match, unavailable Vosk, and confidence handling in tests/unit/test_strict_vosk_fallback.py"
Task: "Add command recognition integration tests proving command mode rejects arbitrary Vosk free-form text and respects closed vocabulary choices in tests/integration/test_command_recognition_runtime.py"
Task: "Add fallback ordering tests proving cloud failure proceeds to strict Vosk only when EGB_STT_STRICT_VOSK_FALLBACK_ENABLED=1 in tests/integration/test_google_cloud_stt_runtime.py"
```

## Parallel Example: User Story 4

```bash
Task: "Add exact-output tests for wake, command, confirmation, and onboarding phrase hints in tests/unit/test_phrase_hints.py"
Task: "Add PocketSphinx compatibility gate tests proving zero default Sphinx candidates and explicit debug-only enablement in tests/unit/test_stt_feature_flags.py and tests/integration/test_command_recognition_runtime.py"
Task: "Update operator documentation for Google Cloud dependency, credentials, feature flags, fallback order, PocketSphinx compatibility, and rollback behavior in docs/STTInfo.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate cloud-primary recognition with fake client responses and unchanged runtime method contracts
5. Stop and demo the optional cloud candidate path before enabling failure/fallback changes broadly

### Incremental Delivery

1. Setup + Foundational establish feature flags, optional imports, shared metadata, and provider compatibility
2. Deliver US1 for successful cloud candidate extraction and runtime compatibility
3. Deliver US2 for safe unavailable/failure behavior and privacy diagnostics
4. Deliver US3 for strict Vosk fallback contracts and no arbitrary local command text
5. Deliver US4 for deterministic phrase hints, PocketSphinx gating, rollback documentation, and full operator clarity
6. Finish with Phase 7 contract refresh and full validation sweep

### Parallel Team Strategy

1. Team completes Setup and Foundational together
2. After Phase 2:
   - Developer A: US1 cloud adapter success path and runtime integration
   - Developer B: US2 failure mapping, timeout/retry, no-credential startup, and privacy diagnostics
   - Developer C: US3 strict Vosk grammar contracts and no-match behavior
   - Developer D: US4 phrase hints, Sphinx gate, provider metadata, and docs
3. Rejoin for cross-story candidate ordering, diagnostics, docs, and full validation

---

## Notes

- `[P]` tasks are parallel-safe only after their prerequisite tasks are complete
- Every user story includes explicit test tasks because this feature touches provider adapters, STT ordering, fallback safety, runtime metadata, and field-safe diagnostics
- Keep runtime authority in `core/` and `core/speech/`; GUI surfaces should observe behavior rather than define recognition policy
- Keep Google Cloud support optional at import time and credential time so CI and local development continue without cloud setup
- Never persist Google credential material or raw user utterances in `settings/user_profile.json`, logs, or release artifacts by default
