# Tasks: Offline Truth and Network Policy Alignment

**Input**: Design documents from `/specs/008-offline-policy-alignment/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are REQUIRED because this feature changes provider metadata,
runtime orchestration, settings application, and safety-critical offline and
degraded behavior.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g. `US1`, `US2`, `US3`)
- Include exact file paths in descriptions

## Path Conventions

- **Current project layout**: `main.py`, `controllers/`, `core/`, `settings/`, `tts/`, `ui/`, `tests/`, `docs/`
- **Feature focus**: provider truth in `core/speech/`, runtime and resolver offline decisions in `core/assistant_runtime.py` and `core/resolver.py`, session connectivity state in `settings/`, and validation coverage in `tests/unit/`, `tests/integration/`, and `tests/smoke/`
- **Specification docs**: `specs/008-offline-policy-alignment/contracts/` and `specs/008-offline-policy-alignment/quickstart.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare shared fixtures, test modules, and documentation touchpoints for Phase 8 work.

- [X] T001 Add connectivity-state and override fixture helpers in `tests/conftest.py`
- [X] T002 [P] Extend provider-truth and persistence test scaffolding in `tests/unit/test_provider_registry.py` and `tests/unit/test_settings_provider_persistence.py`
- [X] T003 [P] Create Phase 8 policy-matrix placeholders in `tests/unit/test_connectivity_state_policy.py`, `tests/integration/test_runtime_offline_policy_matrix.py`, and `tests/smoke/test_offline_truth_quickstart.py`
- [X] T004 [P] Add Phase 8 quickstart and troubleshooting placeholders in `specs/008-offline-policy-alignment/quickstart.md` and `docs/release/troubleshooting.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared connectivity, provider-truth, and structured-policy primitives required by all user stories.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Add failing unit coverage for truthful provider `requires_network` metadata and startup-reset expectations in `tests/unit/test_provider_registry.py` and `tests/unit/test_settings_provider_persistence.py`
- [X] T006 [P] Add failing unit coverage for connectivity-state transitions, override modes, and bounded uncertainty grace handling in `tests/unit/test_connectivity_state_policy.py`
- [X] T007 [P] Add failing integration coverage for runtime override visibility and provider-by-provider offline policy inputs in `tests/integration/test_runtime_offline_policy_matrix.py`
- [X] T008 Define shared connectivity-state, probe-result, and structured offline-policy data models in `core/speech/provider_resolver.py` and `core/command_models.py`
- [X] T009 Implement the injectable TCP-based network probe helper in `core/speech/network_probe.py`
- [X] T010 Correct provider network-dependency metadata and fixture defaults in `core/speech/provider_registry.py` and `tests/conftest.py`
- [X] T011 Introduce session-scoped connectivity override/reset handling and remove startup dependence on persisted `network_available` truth in `settings/settings_manager.py` and `settings/profile_store.py`
- [X] T012 Add shared connectivity and offline-policy observability payload helpers in `core/speech/provider_resolver.py` and `core/assistant_runtime.py`

**Checkpoint**: Foundation ready; user story implementation can begin.

---

## Phase 3: User Story 1 - Safe Offline Guidance (Priority: P1) MVP

**Goal**: Ensure network-dependent commands either refuse safely with truthful localized guidance or use the explicitly approved degraded fallback path.

**Independent Test**: Disable effective connectivity, request a non-allowlisted network-dependent command and an allowlisted fallback-capable command, and verify the assistant emits safe refusal or degraded fallback guidance in the active language without false success.

### Tests for User Story 1

- [X] T013 [P] [US1] Extend unit coverage for safe refusal and on-device fallback decisions in `tests/unit/test_provider_resolver.py` and `tests/unit/test_offline_allowlist_policy.py`
- [X] T014 [P] [US1] Extend integration coverage for non-allowlisted and allowlisted offline command flows in `tests/integration/test_runtime_offline_behavior.py` and `tests/integration/test_runtime_offline_policy_matrix.py`
- [X] T015 [P] [US1] Add smoke coverage for offline command truthfulness and spoken guidance in `tests/smoke/test_offline_truth_quickstart.py`

### Implementation for User Story 1

- [X] T016 [US1] Expand command-level offline-policy evaluation to consume detected connectivity, effective connectivity, provider availability, and allowlist state in `core/speech/provider_resolver.py` and `core/command_models.py`
- [X] T017 [US1] Route resolver-level offline command gating through the structured policy contract in `core/resolver.py`
- [X] T018 [US1] Update runtime command handling to emit truthful safe-refusal and on-device fallback behavior in `core/assistant_runtime.py`
- [X] T019 [US1] Keep explicit offline capability approvals aligned with settings snapshots and runtime context in `settings/settings_manager.py` and `settings/profile_store.py`
- [X] T020 [US1] Emit structured command-level offline diagnostics including override mode and provider-truth fields in `core/assistant_runtime.py` and `core/resolver.py`
- [X] T021 [US1] Run US1 validation (`python -m pytest tests/unit/test_provider_resolver.py tests/unit/test_offline_allowlist_policy.py tests/integration/test_runtime_offline_behavior.py tests/integration/test_runtime_offline_policy_matrix.py tests/smoke/test_offline_truth_quickstart.py -q`) and record SC-001 evidence in `specs/008-offline-policy-alignment/quickstart.md`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Honest Provider State (Priority: P2)

**Goal**: Make startup, degraded-mode behavior, and runtime status reflect the real network dependency of the active speech provider.

**Independent Test**: Start the assistant with `legacy` and `speakkit` under online, offline, uncertain, and development-override states and verify readiness, degraded guidance, and runtime events report one consistent effective provider state.

### Tests for User Story 2

- [X] T022 [P] [US2] Extend unit coverage for startup provider resolution, provider availability, and override reset behavior in `tests/unit/test_provider_registry.py`, `tests/unit/test_provider_resolver.py`, and `tests/unit/test_settings_provider_persistence.py`
- [X] T023 [P] [US2] Add integration coverage for degraded/offline startup readiness and provider-state changes during runtime in `tests/integration/test_provider_failure_paths.py`, `tests/integration/test_wearable_startup_readiness.py`, and `tests/integration/test_runtime_offline_policy_matrix.py`
- [X] T024 [P] [US2] Extend smoke startup scenarios for truthful provider readiness in `tests/smoke/test_speech_provider_quickstart.py` and `tests/smoke/test_offline_truth_quickstart.py`

### Implementation for User Story 2

- [X] T025 [US2] Implement effective connectivity-state computation, startup reset to `auto`, and bounded uncertainty grace-window handling in `core/speech/network_probe.py` and `settings/settings_manager.py`
- [X] T026 [US2] Update startup provider resolution to combine provider availability with effective connectivity truth in `core/speech/provider_resolver.py` and `core/speech/provider_registry.py`
- [X] T027 [US2] Wire probe-backed connectivity refresh and truthful startup/degraded guidance through `core/assistant_runtime.py`
- [X] T028 [US2] Ensure degraded and offline startup speech resolves through approved critical prompt surfaces with no false `ready` state in `core/assistant_runtime.py` and `settings/settings_manager.py`
- [X] T029 [US2] Extend runtime events and troubleshooting guidance with detected connectivity, effective connectivity, provider availability, and grace-window fields in `core/assistant_runtime.py` and `docs/release/troubleshooting.md`
- [X] T030 [US2] Run US2 validation (`python -m pytest tests/unit/test_provider_registry.py tests/unit/test_provider_resolver.py tests/unit/test_settings_provider_persistence.py tests/integration/test_provider_failure_paths.py tests/integration/test_wearable_startup_readiness.py tests/integration/test_runtime_offline_policy_matrix.py tests/smoke/test_speech_provider_quickstart.py tests/smoke/test_offline_truth_quickstart.py -q`) and record SC-002/SC-004/SC-007 evidence in `specs/008-offline-policy-alignment/quickstart.md`

**Checkpoint**: User Stories 1 and 2 are independently functional and testable.

---

## Phase 5: User Story 3 - Reproducible Offline Policy Decisions (Priority: P3)

**Goal**: Provide a deterministic provider-by-provider offline-policy matrix with visible override and connectivity evidence for regression and field validation.

**Independent Test**: Run the offline-policy matrix across provider type, connectivity state, uncertainty windows, override mode, and allowlisted versus non-allowlisted capabilities, then confirm decisions, spoken guidance, and diagnostics are deterministic.

### Tests for User Story 3

- [X] T031 [P] [US3] Extend unit coverage for probe-result serialization, matrix determinism, and override visibility in `tests/unit/test_connectivity_state_policy.py` and `tests/unit/test_provider_resolver.py`
- [X] T032 [P] [US3] Extend integration coverage for the provider/connectivity/override/capability matrix in `tests/integration/test_runtime_offline_policy_matrix.py`
- [X] T033 [P] [US3] Add smoke coverage for end-to-end offline truth validation commands in `tests/smoke/test_offline_truth_quickstart.py`

### Implementation for User Story 3

- [X] T034 [US3] Add matrix-friendly connectivity snapshot helpers and deterministic policy serialization in `settings/settings_manager.py` and `core/speech/provider_resolver.py`
- [X] T035 [US3] Emit startup and command decision evidence for matrix validation in `core/assistant_runtime.py` and `core/command_models.py`
- [X] T036 [US3] Update Phase 8 contracts and operator documentation for connectivity-state and offline-policy evidence in `specs/008-offline-policy-alignment/contracts/connectivity-state-contract.md`, `specs/008-offline-policy-alignment/contracts/offline-policy-decision-contract.md`, and `docs/release/troubleshooting.md`
- [X] T037 [US3] Run US3 validation (`python -m pytest tests/unit/test_connectivity_state_policy.py tests/unit/test_provider_resolver.py tests/integration/test_runtime_offline_policy_matrix.py tests/smoke/test_offline_truth_quickstart.py -q`) and record SC-003/SC-005/SC-006 evidence in `specs/008-offline-policy-alignment/quickstart.md`

**Checkpoint**: All user stories are independently functional and testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup, edge-case coverage, and full validation across stories.

- [X] T038 [P] Refresh operator and release guidance for probe targets, override usage, and offline truth verification in `docs/release/troubleshooting.md` and `docs/release/checklist.md`
- [X] T039 Remove stale persisted-network assumptions and dead offline-truth branches in `settings/profile_store.py`, `settings/settings_manager.py`, `core/speech/provider_registry.py`, and `core/speech/provider_resolver.py`
- [X] T040 [P] Add edge-case regression coverage for stale override restart, probe flapping, and force-online-with-provider-unavailable behavior in `tests/unit/test_connectivity_state_policy.py`, `tests/integration/test_runtime_offline_policy_matrix.py`, and `tests/smoke/test_offline_truth_quickstart.py`
- [X] T041 Run full validation sweep (`python -m pytest tests/unit/test_provider_registry.py tests/unit/test_provider_resolver.py tests/unit/test_settings_provider_persistence.py tests/unit/test_offline_allowlist_policy.py tests/unit/test_connectivity_state_policy.py -q`, `python -m pytest tests/integration/test_runtime_offline_behavior.py tests/integration/test_provider_failure_paths.py tests/integration/test_wearable_startup_readiness.py tests/integration/test_runtime_offline_policy_matrix.py -q`, `python -m pytest tests/smoke/test_speech_provider_quickstart.py tests/smoke/test_offline_truth_quickstart.py -q`, `python -m compileall core settings tests`) and record outputs in `specs/008-offline-policy-alignment/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories
- **User Stories (Phases 3-5)**: Depend on Foundational completion
- **Polish (Phase 6)**: Depends on completion of the user stories selected for release scope

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on other stories
- **US2 (P2)**: Starts after Foundational; shares the same connectivity-state foundation but remains independently testable
- **US3 (P3)**: Starts after Foundational; its final matrix and evidence recording should run after US1 and US2 behaviors are in place

### Within Each User Story

- Write listed tests first and confirm they fail before implementation
- Land data-model and contract-aligned primitives before wiring runtime call sites
- Run the listed validation command and record evidence in `specs/008-offline-policy-alignment/quickstart.md` before marking the story complete

### Parallel Opportunities

- `T002`, `T003`, and `T004` can run in parallel after `T001`
- `T006` and `T007` can run in parallel during Foundational work
- `T013`, `T014`, and `T015` can run in parallel for US1
- `T022`, `T023`, and `T024` can run in parallel for US2
- `T031`, `T032`, and `T033` can run in parallel for US3
- `T038` and `T040` can run in parallel during Polish

---

## Parallel Example: User Story 1

```bash
Task: "Extend unit coverage for safe refusal and on-device fallback decisions in tests/unit/test_provider_resolver.py and tests/unit/test_offline_allowlist_policy.py"
Task: "Extend integration coverage for non-allowlisted and allowlisted offline command flows in tests/integration/test_runtime_offline_behavior.py and tests/integration/test_runtime_offline_policy_matrix.py"
Task: "Add smoke coverage for offline command truthfulness and spoken guidance in tests/smoke/test_offline_truth_quickstart.py"
```

## Parallel Example: User Story 2

```bash
Task: "Implement effective connectivity-state computation, startup reset to auto, and bounded uncertainty grace-window handling in core/speech/network_probe.py and settings/settings_manager.py"
Task: "Update startup provider resolution to combine provider availability with effective connectivity truth in core/speech/provider_resolver.py and core/speech/provider_registry.py"
Task: "Extend runtime events and troubleshooting guidance with detected connectivity, effective connectivity, provider availability, and grace-window fields in core/assistant_runtime.py and docs/release/troubleshooting.md"
```

## Parallel Example: User Story 3

```bash
Task: "Extend unit coverage for probe-result serialization, matrix determinism, and override visibility in tests/unit/test_connectivity_state_policy.py and tests/unit/test_provider_resolver.py"
Task: "Extend integration coverage for the provider/connectivity/override/capability matrix in tests/integration/test_runtime_offline_policy_matrix.py"
Task: "Add smoke coverage for end-to-end offline truth validation commands in tests/smoke/test_offline_truth_quickstart.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate offline safe refusal and allowlisted fallback behavior before widening scope

### Incremental Delivery

1. Setup + Foundational establish truthful provider metadata, probe-backed connectivity state, and structured policy contracts
2. Deliver US1 for safe offline command guidance and approved degraded fallback
3. Deliver US2 for truthful startup and degraded provider readiness
4. Deliver US3 for deterministic matrix coverage and field-validation evidence
5. Finish with Phase 6 polish and full validation sweep

### Parallel Team Strategy

1. Team aligns on Setup and Foundational together
2. After Phase 2:
   - Developer A: US1 offline command truth and fallback behavior
   - Developer B: US2 provider readiness and probe-backed startup behavior
   - Developer C: US3 matrix coverage, contracts, and evidence reporting
3. Rejoin for cross-cutting cleanup and final validation

---

## Notes

- `[P]` tasks are parallel-safe only after their dependency prerequisites are complete
- Every user story includes explicit test tasks because this feature touches constitution-protected runtime, settings, provider, and safety behavior
- Keep degraded and offline spoken guidance routed through the approved critical prompt catalog introduced in Phase 7
- Do not let persisted settings silently reactivate development-only connectivity overrides across sessions
