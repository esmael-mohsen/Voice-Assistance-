# Tasks: Arabic, Bilingual Canonicalization, and Safety Confidence Hardening

**Input**: Design documents from `/specs/020-arabic-command-safety/`  
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Required because this feature changes parser behavior, command
post-processing, runtime confidence decisions, confirmation safety, fallback
handling, and field-safe diagnostics.

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
- **Feature focus**: command canonicalization in
  `core/command_post_processing.py`, integrity gating in
  `core/text_integrity.py`, intent matching in `core/parser.py`,
  confidence and recovery policy in `core/assistant_runtime.py`,
  confirmation interpretation in `core/dialog_policy.py` and
  `core/closed_vocabulary.py`, structured metadata in
  `core/command_models.py`, and validation under `tests/unit/`,
  `tests/integration/`, and `tests/smoke/`
- **Specification docs**: `specs/020-arabic-command-safety/contracts/` and
  `specs/020-arabic-command-safety/quickstart.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare reusable fixtures, validation entry points, and evidence
scaffolding for Phase 20 work.

- [X] T001 Add Phase 20 supported Arabic, bilingual, phonetic, corrupted-text, and risky-command fixtures in `tests/conftest.py`
- [X] T002 [P] Add Phase 20 smoke-validation scaffolding for supported-command and risky-command journeys in `tests/smoke/test_hybrid_command_recognition_quickstart.py` and `tests/smoke/test_command_layer_quickstart.py`
- [X] T003 [P] Add integration harness placeholders for recognition-metadata, language-mismatch, and diagnostics scenarios in `tests/integration/test_command_recognition_runtime.py` and `tests/integration/test_stt_privacy_diagnostics.py`
- [X] T004 [P] Add Phase 20 validation evidence placeholders and operator notes in `specs/020-arabic-command-safety/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared contracts, metadata surfaces, and integrity
boundaries required by all user stories.

**CRITICAL**: No user story work should begin until this phase is complete.

- [X] T005 Add failing normalized-command-candidate and variant-mapping contract coverage for field-safe transcript references in `tests/unit/test_command_post_processing.py` and `tests/unit/test_command_recognition_contract.py`
- [X] T006 [P] Add failing safety-decision and stable-supported-candidate contract coverage in `tests/unit/test_command_confidence_policy.py` and `tests/unit/test_command_safety_evaluation_contract.py`
- [X] T007 [P] Add failing multilingual confirmation and closed-vocabulary parity coverage in `tests/unit/test_dialog_confirmation_policy.py`, `tests/unit/test_closed_vocabulary.py`, and `tests/integration/test_command_confirmation_localization.py`
- [X] T008 Extend shared command metadata and structured result models with integrity, substitution, stable-candidate, and ambiguity fields in `core/command_models.py`
- [X] T009 [P] Add curated variant-mapping and integrity-assessment helper boundaries in `core/command_post_processing.py` and `core/text_integrity.py`
- [X] T010 [P] Propagate canonicalization and recognition metadata through parsing and dispatch boundaries in `core/parser.py`, `core/dispatcher.py`, and `core/assistant_runtime.py`
- [X] T011 [P] Add field-safe command decision diagnostic scaffolding and Phase 20 guidance in `core/runtime_diagnostics.py` and `docs/STTInfo.md`
- [X] T012 [P] Align command-recognition fixtures with the refreshed contracts in `tests/unit/test_command_recognition_contract.py` and `specs/020-arabic-command-safety/contracts/normalized-command-candidate-contract.md`

**Checkpoint**: Shared command contracts and metadata boundaries are ready;
user story work can now begin.

---

## Phase 3: User Story 1 - Understand Supported Arabic And Mixed Commands Reliably (Priority: P1) MVP

**Goal**: Make supported Arabic, Egyptian-Arabic, Arabizi, and mixed-language
command phrases resolve into the intended existing command meaning.

**Independent Test**: Run supported Arabic, Egyptian-Arabic, Arabizi, and
mixed-language command fixtures and verify they resolve to the intended
existing command outcome without requiring a screen.

### Tests for User Story 1

> **NOTE: Write these tests first and ensure they fail before implementation
> because this story changes constitution-protected parser and runtime
> behavior.**

- [X] T013 [P] [US1] Add unit tests for Arabic letter-form normalization, punctuation cleanup, and parser-ready canonical text in `tests/unit/test_command_post_processing.py` and `tests/unit/test_command_canonicalization.py`
- [X] T014 [P] [US1] Add unit tests for curated Arabic, Egyptian-Arabic, bilingual, and Arabizi intent resolution in `tests/unit/test_parser.py`
- [X] T015 [P] [US1] Add integration tests for supported Arabic and mixed-language runtime command recognition across primary and bounded fallback paths in `tests/integration/test_command_recognition_runtime.py` and `tests/integration/test_hybrid_command_recognition.py`
- [X] T016 [P] [US1] Add smoke coverage for supported Arabic and mixed-language command journeys in `tests/smoke/test_hybrid_command_recognition_quickstart.py` and `tests/smoke/test_command_layer_quickstart.py`

### Implementation for User Story 1

- [X] T017 [US1] Implement curated Arabic, Egyptian-Arabic, bilingual, and phonetic variant-mapping rules in `core/command_post_processing.py`
- [X] T018 [US1] Expand the supported command inventory so mapped Arabic and mixed-language phrases stay tied to existing intent IDs in `core/parser.py`
- [X] T019 [US1] Preserve parser-ready canonical command selection and language hints for supported mapped candidates in `core/assistant_runtime.py`
- [X] T020 [US1] Keep command fallback recognition aligned with the supported curated inventory in `core/stt.py` and `tests/conftest.py`
- [X] T021 [US1] Run `python -m pytest tests/unit/test_command_post_processing.py tests/unit/test_command_canonicalization.py tests/unit/test_parser.py tests/integration/test_command_recognition_runtime.py tests/integration/test_hybrid_command_recognition.py tests/smoke/test_hybrid_command_recognition_quickstart.py tests/smoke/test_command_layer_quickstart.py -q` and record SC-001 and SC-002 evidence in `specs/020-arabic-command-safety/quickstart.md`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Keep Safety Strict For Risky Commands (Priority: P2)

**Goal**: Preserve strict confirmation and non-execution safeguards for
protected and medium-risk commands even when normalization or mixed-language
support improves command recognition.

**Independent Test**: Run protected-command fixtures with clean, ambiguous,
conflicting, and near-miss transcripts and verify that only explicitly
confirmed risky actions can proceed.

### Tests for User Story 2

- [X] T022 [P] [US2] Add unit tests for protected-command ambiguity, conflicting alternatives, and language-mismatch confirmation in `tests/unit/test_command_confidence_policy.py` and `tests/unit/test_command_safety_evaluation_contract.py`
- [X] T023 [P] [US2] Add unit tests for risky-command near-miss, partial-match, and unsupported-phrase rejection in `tests/unit/test_parser.py` and `tests/unit/test_command_post_processing.py`
- [X] T024 [P] [US2] Add integration tests for protected-command confirmation behavior and low-risk clean execution parity in `tests/integration/test_command_dialog_robustness.py` and `tests/integration/test_command_confirmation_localization.py`
- [X] T025 [P] [US2] Add smoke coverage for protected-command confirmation and safe non-execution outcomes in `tests/smoke/test_command_layer_quickstart.py`

### Implementation for User Story 2

- [X] T026 [US2] Mark high-impact substitutions and stable supported candidates for risky-command flows in `core/command_post_processing.py` and `core/assistant_runtime.py`
- [X] T027 [US2] Tighten parser risk-tier tie-breaks and supported-boundary handling for protected and medium-risk commands in `core/parser.py`
- [X] T028 [US2] Require confirmation for medium-risk stable candidates under ambiguity, language mismatch, conflicting alternatives, or borderline confidence in `core/assistant_runtime.py`
- [X] T029 [US2] Preserve multilingual yes/no/cancel safety precedence for risky-command confirmation turns in `core/dialog_policy.py`, `core/closed_vocabulary.py`, and `core/resolver.py`
- [X] T030 [US2] Run `python -m pytest tests/unit/test_command_confidence_policy.py tests/unit/test_command_safety_evaluation_contract.py tests/unit/test_parser.py tests/unit/test_command_post_processing.py tests/integration/test_command_dialog_robustness.py tests/integration/test_command_confirmation_localization.py tests/smoke/test_command_layer_quickstart.py -q` and record SC-003 evidence in `specs/020-arabic-command-safety/quickstart.md`

**Checkpoint**: User Stories 1 and 2 are independently functional and testable.

---

## Phase 5: User Story 3 - Reject Corrupted And Unsafe Text Safely (Priority: P3)

**Goal**: Ensure corrupted Arabic-like text, mojibake, unsupported near-command
phrases, and unstable language-mismatch cases fail through bounded retry or
safe refusal instead of misexecution.

**Independent Test**: Run corrupted-text, mojibake, unsupported phrase, and
language-mismatch fixtures and verify the assistant retries, confirms, or
refuses safely instead of misexecuting.

### Tests for User Story 3

- [X] T031 [P] [US3] Add unit tests for corrupted Arabic-like text, mojibake, and unexpected-Unicode rejection in `tests/unit/test_command_post_processing.py` and `tests/unit/test_parser.py`
- [X] T032 [P] [US3] Add unit tests for non-protected bounded retry and protected safe-refusal behavior in `tests/unit/test_command_safety_evaluation_contract.py` and `tests/unit/test_command_confidence_policy.py`
- [X] T033 [P] [US3] Add integration tests for corrupted-text, unsupported near-command, and language-mismatch runtime recovery in `tests/integration/test_command_recognition_runtime.py` and `tests/integration/test_hybrid_command_recognition.py`
- [X] T034 [P] [US3] Add smoke coverage for corrupted and unsafe near-command rejection in `tests/smoke/test_hybrid_command_recognition_quickstart.py` and `tests/smoke/test_command_layer_quickstart.py`

### Implementation for User Story 3

- [X] T035 [US3] Strengthen mojibake, corruption, and unexpected-Unicode detection for command transcripts in `core/text_integrity.py` and `core/command_post_processing.py`
- [X] T036 [US3] Reject corrupted and unsupported near-command candidates before executable parser acceptance in `core/parser.py` and `core/command_post_processing.py`
- [X] T037 [US3] Route corrupted, unstable, and language-mismatch command cases through bounded retry or safe refusal in `core/assistant_runtime.py`
- [X] T038 [US3] Align bounded fallback recognition with the same corruption and unsupported-command safety rules in `core/assistant_runtime.py` and `core/stt.py`
- [X] T039 [US3] Run `python -m pytest tests/unit/test_command_post_processing.py tests/unit/test_parser.py tests/unit/test_command_safety_evaluation_contract.py tests/unit/test_command_confidence_policy.py tests/integration/test_command_recognition_runtime.py tests/integration/test_hybrid_command_recognition.py tests/smoke/test_hybrid_command_recognition_quickstart.py tests/smoke/test_command_layer_quickstart.py -q` and record SC-004 evidence in `specs/020-arabic-command-safety/quickstart.md`

**Checkpoint**: User Stories 1 through 3 are independently functional and testable.

---

## Phase 6: User Story 4 - Explain Major Normalization Decisions Safely (Priority: P4)

**Goal**: Emit field-safe metadata that explains normalization, ambiguity, and
safety decisions without storing raw utterance content.

**Independent Test**: Exercise accepted, confirmed, retried, refused, and
rejected command fixtures and verify the emitted metadata explains major
normalization and safety decisions without raw user content.

### Tests for User Story 4

- [X] T040 [P] [US4] Add unit contract tests for integrity status, substitution markers, stable-candidate state, field-safe transcript references, and ambiguity metadata in `tests/unit/test_command_recognition_contract.py` and `tests/unit/test_command_fallback_decision_contract.py`
- [X] T041 [P] [US4] Add integration tests for field-safe accepted, confirmed, retried, refused, and rejected command diagnostics in `tests/integration/test_stt_privacy_diagnostics.py` and `tests/integration/test_command_recognition_runtime.py`
- [X] T042 [P] [US4] Add smoke coverage for metadata-only decision tracing in `tests/smoke/test_hybrid_command_recognition_quickstart.py`

### Implementation for User Story 4

- [X] T043 [US4] Extend normalized-candidate and safety-decision payloads with integrity status, substitution markers, stable-supported-candidate state, language mismatch, and alternative-conflict metadata in `core/command_models.py` and `core/assistant_runtime.py`
- [X] T044 [US4] Emit field-safe command decision diagnostics across dispatch and runtime paths in `core/dispatcher.py`, `core/runtime_diagnostics.py`, and `core/assistant_runtime.py`
- [X] T045 [US4] Update operator diagnostics guidance and Phase 20 evidence notes in `docs/STTInfo.md` and `specs/020-arabic-command-safety/quickstart.md`
- [X] T046 [US4] Run `python -m pytest tests/unit/test_command_recognition_contract.py tests/unit/test_command_fallback_decision_contract.py tests/integration/test_stt_privacy_diagnostics.py tests/integration/test_command_recognition_runtime.py tests/smoke/test_hybrid_command_recognition_quickstart.py -q` and record SC-005 evidence in `specs/020-arabic-command-safety/quickstart.md`

**Checkpoint**: All user stories are independently functional and testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Reconcile the implementation with the Phase 20 contracts, docs,
and full validation sweep.

- [X] T047 [P] Reconcile shipped Phase 20 behavior with `specs/020-arabic-command-safety/contracts/normalized-command-candidate-contract.md`, `specs/020-arabic-command-safety/contracts/variant-mapping-rule-contract.md`, `specs/020-arabic-command-safety/contracts/safety-decision-record-contract.md`, and `specs/020-arabic-command-safety/contracts/confirmation-dialog-safety-contract.md`
- [X] T048 [P] Refresh Phase 20 rollout, diagnostics, and command-safety notes in `docs/STTInfo.md` and `docs/implementationPlan.md`
- [X] T049 Run `python -m pytest tests/unit/test_command_post_processing.py tests/unit/test_command_canonicalization.py tests/unit/test_parser.py tests/unit/test_command_confidence_policy.py tests/unit/test_command_safety_evaluation_contract.py tests/unit/test_command_recognition_contract.py tests/unit/test_command_fallback_decision_contract.py tests/unit/test_dialog_confirmation_policy.py tests/unit/test_closed_vocabulary.py -q` and record results in `specs/020-arabic-command-safety/quickstart.md`
- [X] T050 Run `python -m pytest tests/integration/test_command_recognition_runtime.py tests/integration/test_hybrid_command_recognition.py tests/integration/test_command_dialog_robustness.py tests/integration/test_command_confirmation_localization.py tests/integration/test_stt_privacy_diagnostics.py tests/smoke/test_hybrid_command_recognition_quickstart.py tests/smoke/test_command_layer_quickstart.py -q` and record results in `specs/020-arabic-command-safety/quickstart.md`
- [X] T051 Run `python -m compileall core tests` and `python -m ruff check .` and record results in `specs/020-arabic-command-safety/quickstart.md`
- [X] T052 Review `core/assistant_runtime.py`, `core/command_post_processing.py`, `core/text_integrity.py`, `core/runtime_diagnostics.py`, and `settings/user_profile.json` for raw-utterance persistence or unsafe metadata leakage and confirm the privacy audit in `specs/020-arabic-command-safety/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1: Setup** has no dependencies.
- **Phase 2: Foundational** depends on Setup and blocks all user stories.
- **Phase 3: US1** depends on Foundational and is the MVP.
- **Phase 4: US2** depends on Foundational and validates against the safer
  canonicalization path delivered by US1 while remaining independently
  testable.
- **Phase 5: US3** depends on Foundational and should validate after the
  shared metadata path from US1 and US2 exists.
- **Phase 6: US4** depends on Foundational and should validate after the
  normalization and safety outcomes from US1 through US3 are settled.
- **Phase 7: Polish** depends on the selected user stories being complete.

### User Story Dependencies

- **US1 (P1)**: No dependency on other stories after Foundational; delivers
  the command-understanding MVP.
- **US2 (P2)**: Depends on Foundational; final verification should run after
  US1 because it tightens confirmation and risk behavior around the improved
  mapping path.
- **US3 (P3)**: Depends on Foundational; final verification should run after
  US1 and US2 because it rejects unsafe edge cases across the same command
  pipeline.
- **US4 (P4)**: Depends on Foundational; final verification should run after
  US1 through US3 because it describes their decision metadata.

### Within Each User Story

- Write the listed tests first and confirm they fail before implementation.
- Land shared metadata or contract changes before runtime-integration changes.
- Keep confirmation and recovery behavior field-safe before marking a story
  complete.
- Run the story-specific validation command from `quickstart.md` before moving
  to the next checkpoint.

### Parallel Opportunities

- `T002`, `T003`, and `T004` can run in parallel after `T001`.
- `T006`, `T007`, `T009`, `T010`, `T011`, and `T012` can run in parallel
  during Foundational work.
- `T013`, `T014`, `T015`, and `T016` can run in parallel for US1.
- `T022`, `T023`, `T024`, and `T025` can run in parallel for US2.
- `T031`, `T032`, `T033`, and `T034` can run in parallel for US3.
- `T040`, `T041`, and `T042` can run in parallel for US4.
- `T047` and `T048` can run in parallel during Polish.

---

## Parallel Example: User Story 1

```text
Task: "T013 [P] [US1] Add unit tests for Arabic letter-form normalization, punctuation cleanup, and parser-ready canonical text in tests/unit/test_command_post_processing.py and tests/unit/test_command_canonicalization.py"
Task: "T014 [P] [US1] Add unit tests for curated Arabic, Egyptian-Arabic, bilingual, and Arabizi intent resolution in tests/unit/test_parser.py"
Task: "T015 [P] [US1] Add integration tests for supported Arabic and mixed-language runtime command recognition across primary and bounded fallback paths in tests/integration/test_command_recognition_runtime.py and tests/integration/test_hybrid_command_recognition.py"
Task: "T016 [P] [US1] Add smoke coverage for supported Arabic and mixed-language command journeys in tests/smoke/test_hybrid_command_recognition_quickstart.py and tests/smoke/test_command_layer_quickstart.py"
```

## Parallel Example: User Story 2

```text
Task: "T022 [P] [US2] Add unit tests for protected-command ambiguity, conflicting alternatives, and language-mismatch confirmation in tests/unit/test_command_confidence_policy.py and tests/unit/test_command_safety_evaluation_contract.py"
Task: "T023 [P] [US2] Add unit tests for risky-command near-miss, partial-match, and unsupported-phrase rejection in tests/unit/test_parser.py and tests/unit/test_command_post_processing.py"
Task: "T024 [P] [US2] Add integration tests for protected-command confirmation behavior and low-risk clean execution parity in tests/integration/test_command_dialog_robustness.py and tests/integration/test_command_confirmation_localization.py"
Task: "T025 [P] [US2] Add smoke coverage for protected-command confirmation and safe non-execution outcomes in tests/smoke/test_command_layer_quickstart.py"
```

## Parallel Example: User Story 3

```text
Task: "T031 [P] [US3] Add unit tests for corrupted Arabic-like text, mojibake, and unexpected-Unicode rejection in tests/unit/test_command_post_processing.py and tests/unit/test_parser.py"
Task: "T032 [P] [US3] Add unit tests for non-protected bounded retry and protected safe-refusal behavior in tests/unit/test_command_safety_evaluation_contract.py and tests/unit/test_command_confidence_policy.py"
Task: "T033 [P] [US3] Add integration tests for corrupted-text, unsupported near-command, and language-mismatch runtime recovery in tests/integration/test_command_recognition_runtime.py and tests/integration/test_hybrid_command_recognition.py"
Task: "T034 [P] [US3] Add smoke coverage for corrupted and unsafe near-command rejection in tests/smoke/test_hybrid_command_recognition_quickstart.py and tests/smoke/test_command_layer_quickstart.py"
```

## Parallel Example: User Story 4

```text
Task: "T040 [P] [US4] Add unit contract tests for integrity status, substitution markers, stable-candidate state, field-safe transcript references, and ambiguity metadata in tests/unit/test_command_recognition_contract.py and tests/unit/test_command_fallback_decision_contract.py"
Task: "T041 [P] [US4] Add integration tests for field-safe accepted, confirmed, retried, refused, and rejected command diagnostics in tests/integration/test_stt_privacy_diagnostics.py and tests/integration/test_command_recognition_runtime.py"
Task: "T042 [P] [US4] Add smoke coverage for metadata-only decision tracing in tests/smoke/test_hybrid_command_recognition_quickstart.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup tasks.
2. Complete Phase 2 foundational tasks.
3. Complete Phase 3 User Story 1 tasks.
4. Stop and validate supported Arabic and mixed-language command resolution
   before widening scope.

### Incremental Delivery

1. Deliver US1 for reliable Arabic and mixed-language command understanding.
2. Deliver US2 for protected-command safety and confirmation strictness.
3. Deliver US3 for corruption rejection and unsafe-edge-case recovery.
4. Deliver US4 for field-safe metadata and operator visibility.
5. Finish with Phase 7 reconciliation and full validation.

### Parallel Team Strategy

1. Complete Setup and Foundational work together.
2. After Phase 2:
   - Developer A: US1 supported-command mapping and parser alignment
   - Developer B: US2 risk policy and confirmation behavior
   - Developer C: US3 corruption rejection and fallback safety
   - Developer D: US4 diagnostics and metadata contracts
3. Rejoin for Phase 7 validation and documentation cleanup.

---

## Notes

- Tests are intentionally first because this feature touches constitution-
  protected parser, runtime, fallback, and safety paths.
- Keep executable command scope bounded to the existing catalog even when new
  spoken variants are added.
- Do not auto-learn executable phrases from field utterances.
- Do not persist raw utterances in command diagnostics, quickstart evidence,
  or release artifacts by default.

