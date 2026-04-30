# Tasks: STT Observability, Rollout Gates, and PocketSphinx Decommission

**Input**: Design documents from `/specs/021-stt-rollout-observability/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are REQUIRED because this feature touches runtime STT behavior, provider fallback, diagnostics, release gates, rollout safety, and bounded recovery.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and does not depend on incomplete tasks.
- **[Story]**: User story label for traceability. Setup, foundational, and polish tasks do not use story labels.
- **File paths**: Every task names the exact repository path to change or validate.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare deterministic fixtures and evidence scaffolding shared by all stories.

- [X] T001 Create shared STT rollout fixture overview in tests/fixtures/stt_rollout_observability/README.md
- [X] T002 [P] Create field-safe STT telemetry event fixture examples in tests/fixtures/stt_rollout_observability/stt_events.json
- [X] T003 [P] Create STT telemetry rollup fixture examples in tests/fixtures/stt_rollout_observability/stt_rollups.json
- [X] T004 [P] Create STT failure scenario fixture matrix in tests/fixtures/stt_rollout_observability/failure_scenarios.json
- [X] T005 [P] Create rollout gate, Pi 4, and PocketSphinx evidence fixture index in tests/fixtures/stt_rollout_observability/evidence_index.json

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define shared models, redaction, artifact persistence, and threshold plumbing required by every story.

**CRITICAL**: No user story implementation should begin until this phase is complete.

- [X] T006 Define STT telemetry, rollout, failure scenario, release gate, Pi 4 qualification, and PocketSphinx decommission models in core/release_models.py
- [X] T007 Add field-safe STT payload builders and raw content redaction guards in core/runtime_diagnostics.py
- [X] T008 Extend speech telemetry storage and aggregation primitives for events and rollups in core/release_metrics.py
- [X] T009 Extend local release artifact persistence for STT events, rollups, gate evidence, Pi 4 snapshots, and decommission evidence in core/release_artifacts.py
- [X] T010 Update approved STT recognition threshold keys and Pi 4 threshold mapping in settings/release_thresholds.json and core/release_gates.py
- [X] T011 [P] Add shared STT evidence fixture builders for unit and integration tests in tests/conftest.py
- [X] T012 Add foundational privacy regression tests for STT diagnostic redaction in tests/unit/test_runtime_diagnostics.py

**Checkpoint**: Foundation ready. User story work can now proceed in priority order or in parallel by separate contributors.

---

## Phase 3: User Story 1 - Understand STT Behavior In The Field (Priority: P1) MVP

**Goal**: Emit field-safe STT telemetry events and per-run rollups for cloud attempts, fallback, retries, clipping, timeouts, Arabic failures, and language mismatch without raw audio or raw utterances.

**Independent Test**: Exercise representative cloud, fallback, retry, timeout, clipping, confidence, Arabic-failure, and language-mismatch fixtures and verify each emits field-safe event records plus rollups with source, rollout mode, status, confidence bucket, latency bucket, failure category, recovery outcome, and reason codes only.

### Tests for User Story 1

- [X] T013 [P] [US1] Add contract tests for STT telemetry event and rollup field rules in tests/unit/test_stt_observability_contract.py
- [X] T014 [P] [US1] Add integration tests for cloud, strict fallback, rescue, retry, clipping, timeout, Arabic-failure, and language-mismatch telemetry in tests/integration/test_stt_observability_pipeline.py

### Implementation for User Story 1

- [X] T015 [US1] Wire STT telemetry event creation into VoiceListener cloud, strict Vosk, rescue, clipping, timeout, and language mismatch paths in core/stt.py
- [X] T016 [US1] Emit command recognition telemetry and fallback or retry outcomes through AssistantRuntime._emit_recognition_telemetry in core/assistant_runtime.py
- [X] T017 [US1] Generate per-session and per-candidate STT rollups from recorded telemetry events in core/release_metrics.py
- [X] T018 [US1] Persist local STT events and rollups with 180-day retention metadata in core/release_artifacts.py
- [X] T019 [US1] Add field-safe runtime diagnostic fields for source, rollout mode, status, confidence bucket, latency bucket, failure category, recovery outcome, and reason code in core/runtime_diagnostics.py
- [X] T020 [US1] Document STT telemetry event and rollup troubleshooting expectations in docs/release/troubleshooting.md

**Checkpoint**: User Story 1 is independently testable and provides the MVP observability baseline.

---

## Phase 4: User Story 2 - Gate Cloud-Primary Rollout Safely (Priority: P2)

**Goal**: Block unsafe cloud-primary rollout when cloud configuration, strict fallback, wake fallback, protected-command safety, bilingual behavior, bounded recovery, Pi 4 qualification, or PocketSphinx exclusion regresses.

**Independent Test**: Run release validation with passing and failing configuration, fallback, protected-command, bilingual, wake fallback, PocketSphinx, and Pi 4 qualification evidence and verify safety-critical regressions block pilot and field readiness.

### Tests for User Story 2

- [X] T021 [P] [US2] Add unit tests for rollout mode ordering, rollback precedence, and release gate contract behavior in tests/unit/test_stt_rollout_modes.py
- [X] T022 [P] [US2] Add integration tests for blocking STT rollout release gates in tests/integration/test_stt_rollout_release_gates.py
- [X] T023 [P] [US2] Extend Pi 4 qualification gate tests for recognition latency, CPU, memory, and telemetry completeness in tests/integration/test_pi_qualification_release_gates.py

### Implementation for User Story 2

- [X] T024 [US2] Implement rollout mode ordering, skipped-stage rejection, and rollback override validation in core/release_gates.py
- [X] T025 [US2] Wire requested and effective STT rollout mode metadata into AssistantRuntime config and status diagnostics in core/assistant_runtime.py
- [X] T026 [US2] Extend speech release gates for cloud config, strict fallback, wake fallback, protected-command, bilingual, bounded recovery, Pi 4, and PocketSphinx blocking conditions in core/release_gates.py
- [X] T027 [US2] Add release validation CLI ingestion and reporting for STT rollout evidence artifacts in scripts/release_validate.py
- [X] T028 [US2] Extend PiQualificationRunRecord and Pi 4 gate evaluation for wake latency, command recognition latency, fallback latency, CPU, and memory evidence in core/release_models.py and core/release_gates.py
- [X] T029 [US2] Document Pi 4 STT rollout qualification evidence and blocking thresholds in docs/release/audio_frontend_qualification.md

**Checkpoint**: User Story 2 is independently testable through release validation using fixture evidence and Pi 4 qualification snapshots.

---

## Phase 5: User Story 3 - Recover Predictably From STT Failure Scenarios (Priority: P3)

**Goal**: Classify STT failure scenarios and resolve each to fallback, retry, safe refusal, or standby without an unhandled crash.

**Independent Test**: Run no-network, missing-credential, expired-credential, quota/rate, cloud-timeout, missing-fallback, microphone-timeout, repeated-clipping, and language-mismatch fixtures and verify each returns a bounded user-safe result with field-safe diagnostics.

### Tests for User Story 3

- [X] T030 [P] [US3] Add unit tests for failure category mapping and bounded outcome contracts in tests/unit/test_stt_failure_scenario_contract.py
- [X] T031 [P] [US3] Add integration tests for covered STT failure recovery scenarios in tests/integration/test_stt_failure_scenario_recovery.py

### Implementation for User Story 3

- [X] T032 [US3] Classify network, credential, quota/rate, cloud timeout, fallback missing, microphone timeout, clipping, language mismatch, and confidence-policy failures in core/stt.py
- [X] T033 [US3] Convert classified STT failures into bounded fallback, retry, safe refusal, or standby outcomes in core/assistant_runtime.py
- [X] T034 [US3] Add field-safe failure scenario payloads, reason codes, and raw-content exclusion checks in core/runtime_diagnostics.py
- [X] T035 [US3] Record failure scenario results and crash-free outcome counts in core/release_metrics.py
- [X] T036 [US3] Add release gate checks for bounded recovery completeness and failed recovery regressions in core/release_gates.py
- [X] T037 [US3] Update short non-visual STT recovery prompt guidance in core/dialog_policy.py

**Checkpoint**: User Story 3 is independently testable and proves covered STT failures recover predictably.

---

## Phase 6: User Story 4 - Decommission PocketSphinx From The Active STT Path (Priority: P4)

**Goal**: Prove default production recognition has zero PocketSphinx candidates or invocations while documenting any remaining compatibility-only path.

**Independent Test**: Inspect release dependencies, default runtime behavior, required accuracy baselines, and STT documentation to verify PocketSphinx is not required for production recognition and compatibility is explicit.

### Tests for User Story 4

- [X] T038 [P] [US4] Add unit tests for PocketSphinx decommission evidence and production-baseline exclusion in tests/unit/test_pocketsphinx_decommission_contract.py
- [X] T039 [P] [US4] Add integration tests proving default recognition produces zero PocketSphinx candidates and invocations in tests/integration/test_pocketsphinx_decommission.py

### Implementation for User Story 4

- [X] T040 [US4] Add default PocketSphinx candidate and invocation evidence counters while preserving explicit compatibility-only behavior in core/stt.py
- [X] T041 [US4] Add PocketSphinx decommission serialization and production-baseline exclusion checks in core/release_models.py
- [X] T042 [US4] Fail release readiness when default PocketSphinx candidate or invocation evidence is non-zero in core/release_gates.py
- [X] T043 [US4] Add release validation reporting for PocketSphinx decommission evidence in scripts/release_validate.py
- [X] T044 [US4] Update cloud-primary, strict fallback, and PocketSphinx compatibility-only status in docs/STTInfo.md
- [X] T045 [US4] Update PocketSphinx troubleshooting and rollback boundaries in docs/release/troubleshooting.md

**Checkpoint**: User Story 4 is independently testable and proves PocketSphinx is outside active production STT requirements.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Complete smoke validation, documentation links, and final quality gates after selected user stories are complete.

- [X] T046 [P] Add end-to-end quickstart smoke test for STT rollout observability in tests/smoke/test_stt_rollout_observability_quickstart.py
- [X] T047 [P] Update Phase 21 validation command sequence and evidence locations in docs/release/startup.md
- [X] T048 Create STT rollout observability validation record template in docs/release/stt_rollout_observability_validation.md
- [X] T049 Run unit tests for STT observability, rollout modes, failure scenarios, and PocketSphinx decommission and append the result to docs/release/stt_rollout_observability_validation.md
- [X] T050 Run integration and smoke tests for STT observability, rollout release gates, failure recovery, Pi 4 qualification, and quickstart and append the result to docs/release/stt_rollout_observability_validation.md
- [X] T051 Run `python -m compileall core tests scripts` and `python -m ruff check .`, then append the result to docs/release/stt_rollout_observability_validation.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1 and blocks all user stories.
- **Phase 3 US1**: Depends on Phase 2 and is the MVP.
- **Phase 4 US2**: Depends on Phase 2. It can start after foundation, but final release-gate confidence is stronger once US1 telemetry evidence exists.
- **Phase 5 US3**: Depends on Phase 2. It can run independently, but US2 consumes its bounded recovery evidence for blocking gates.
- **Phase 6 US4**: Depends on Phase 2. It can run independently, but US2 consumes its decommission evidence for blocking gates.
- **Phase 7 Polish**: Depends on all selected user stories.

### User Story Dependencies

- **US1 (P1)**: No dependency on other stories after foundation. Delivers MVP observability.
- **US2 (P2)**: Independently testable with fixtures after foundation. Integrates US1, US3, and US4 evidence for final release confidence.
- **US3 (P3)**: Independently testable with failure fixtures after foundation.
- **US4 (P4)**: Independently testable with default recognition and release baseline fixtures after foundation.

### Within Each User Story

- Write the listed tests first and confirm they fail before implementation.
- Add or update shared models before runtime wiring.
- Add runtime wiring before release validation ingestion.
- Add diagnostics and documentation before the story checkpoint.
- Stop at each checkpoint to validate the story independently.

---

## Parallel Opportunities

- Setup fixture tasks T002, T003, T004, and T005 can run in parallel.
- Foundational helper task T011 can run in parallel with model and runtime work once fixture shape is agreed.
- US1 tests T013 and T014 can run in parallel before implementation.
- US2 tests T021, T022, and T023 can run in parallel before implementation.
- US3 tests T030 and T031 can run in parallel before implementation.
- US4 tests T038 and T039 can run in parallel before implementation.
- After Phase 2, US1, US2, US3, and US4 can be assigned to separate contributors as long as edits to shared files are coordinated.
- Polish tasks T046 and T047 can run in parallel after relevant stories are complete.

---

## Parallel Example: User Story 1

```powershell
# Contract and integration tests can be authored together:
Task: "T013 Add contract tests for STT telemetry event and rollup field rules in tests/unit/test_stt_observability_contract.py"
Task: "T014 Add integration tests for cloud, strict fallback, rescue, retry, clipping, timeout, Arabic-failure, and language-mismatch telemetry in tests/integration/test_stt_observability_pipeline.py"
```

## Parallel Example: User Story 2

```powershell
# Release gate coverage can be split by validation layer:
Task: "T021 Add unit tests for rollout mode ordering, rollback precedence, and release gate contract behavior in tests/unit/test_stt_rollout_modes.py"
Task: "T022 Add integration tests for blocking STT rollout release gates in tests/integration/test_stt_rollout_release_gates.py"
Task: "T023 Extend Pi 4 qualification gate tests for recognition latency, CPU, memory, and telemetry completeness in tests/integration/test_pi_qualification_release_gates.py"
```

## Parallel Example: User Story 3

```powershell
# Failure taxonomy and runtime recovery tests can be authored together:
Task: "T030 Add unit tests for failure category mapping and bounded outcome contracts in tests/unit/test_stt_failure_scenario_contract.py"
Task: "T031 Add integration tests for covered STT failure recovery scenarios in tests/integration/test_stt_failure_scenario_recovery.py"
```

## Parallel Example: User Story 4

```powershell
# Decommission evidence and runtime default behavior can be tested separately:
Task: "T038 Add unit tests for PocketSphinx decommission evidence and production-baseline exclusion in tests/unit/test_pocketsphinx_decommission_contract.py"
Task: "T039 Add integration tests proving default recognition produces zero PocketSphinx candidates and invocations in tests/integration/test_pocketsphinx_decommission.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup fixtures.
2. Complete Phase 2 shared models, redaction, aggregation, artifacts, and threshold plumbing.
3. Complete Phase 3 US1 telemetry events and rollups.
4. Stop and validate US1 with `tests/unit/test_stt_observability_contract.py` and `tests/integration/test_stt_observability_pipeline.py`.

### Incremental Delivery

1. Deliver US1 to make STT behavior observable.
2. Deliver US2 to block unsafe rollout with release gates.
3. Deliver US3 to prove bounded recovery for covered failure scenarios.
4. Deliver US4 to complete PocketSphinx decommission evidence.
5. Run Phase 7 validation and update release documentation.

### Parallel Team Strategy

1. Complete Setup and Foundational phases together.
2. Assign US1 telemetry, US2 release gates, US3 failure recovery, and US4 decommission evidence to separate contributors.
3. Coordinate shared edits in core/release_models.py, core/release_gates.py, core/release_metrics.py, core/runtime_diagnostics.py, core/stt.py, and core/assistant_runtime.py.
4. Merge by story checkpoints and finish with the Phase 7 quality gates.

---

## Task Summary

- **Total tasks**: 51
- **Setup tasks**: 5
- **Foundational tasks**: 7
- **US1 tasks**: 8
- **US2 tasks**: 9
- **US3 tasks**: 8
- **US4 tasks**: 8
- **Polish tasks**: 6
- **MVP scope**: Phase 1, Phase 2, and Phase 3 (US1)
