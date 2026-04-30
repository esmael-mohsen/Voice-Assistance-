# Tasks: Localization Integrity and Prompt Hardening

**Input**: Design documents from `/specs/007-localization-prompt-hardening/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are REQUIRED because this feature changes runtime orchestration, settings application, resolver safety prompts, and release-blocking localization validation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g. `US1`, `US2`, `US3`)
- Include exact file paths in descriptions

## Path Conventions

- **Current project layout**: `main.py`, `controllers/`, `core/`, `settings/`, `tts/`, `ui/`, `tests/`, `docs/`
- **Feature focus**: prompt catalog and resolution logic in `settings/` and `core/`, critical runtime surfaces in `core/assistant_runtime.py` and `core/resolver.py`, release validation in `core/release_localization.py`, and validation coverage in `tests/unit/`, `tests/integration/`, and `tests/smoke/`
- **Specification docs**: `specs/007-localization-prompt-hardening/contracts/` and `specs/007-localization-prompt-hardening/quickstart.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare shared fixtures, test modules, and operator documentation touchpoints for Phase 7 work.

- [X] T001 Add critical-prompt catalog fixture helpers and corrupted-catalog reset utilities in `tests/conftest.py`
- [X] T002 [P] Create catalog normalization and fallback unit test module in `tests/unit/test_settings_critical_prompt_catalog.py`
- [X] T003 [P] Create runtime localization integration test modules in `tests/integration/test_runtime_prompt_localization.py` and `tests/integration/test_command_confirmation_localization.py`
- [X] T004 [P] Add Phase 7 localization validation placeholders in `specs/007-localization-prompt-hardening/quickstart.md` and `docs/release/troubleshooting.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared catalog, surface-binding, and integrity primitives required by all user stories.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Add failing unit coverage for required prompt keys, seeded repair, and same-language fallback in `tests/unit/test_settings_critical_prompt_catalog.py`
- [X] T006 [P] Add failing unit coverage for mojibake-pattern classification and failure reasons in `tests/unit/test_release_localization_integrity.py`
- [X] T007 [P] Add failing integration coverage for catalog-plus-surface validation contracts in `tests/integration/test_release_localization_validation.py`
- [X] T008 Implement shared critical prompt catalog, required key inventory, and surface-binding registry in `core/critical_prompts.py`
- [X] T009 Implement persisted catalog normalization, repair, and emergency-fallback seeding in `settings/settings_manager.py` and `settings/profile_store.py`
- [X] T010 Align the approved baseline critical prompt catalog entries in `settings/user_profile.json`
- [X] T011 Implement deterministic Arabic corruption-pattern helpers and shared failure enums in `core/release_localization.py` and `core/critical_prompts.py`
- [X] T012 Add shared prompt-integrity observability scaffolding for runtime and release validation in `core/assistant_runtime.py` and `core/release_localization.py`

**Checkpoint**: Foundation ready; user story implementation can begin.

---

## Phase 3: User Story 1 - Hear Correct Arabic Guidance (Priority: P1) MVP

**Goal**: Deliver readable Arabic startup, onboarding, interrupt, and offline guidance with safe same-language fallback when catalog entries are corrupt.

**Independent Test**: Run an Arabic runtime/onboarding flow and verify startup, onboarding, interrupt, and offline critical prompts are readable and degrade to approved Arabic fallback with an integrity signal when corrupted.

### Tests for User Story 1

- [X] T013 [P] [US1] Add unit coverage for readable prompt selection and runtime fallback repair paths in `tests/unit/test_settings_critical_prompt_catalog.py` and `tests/unit/test_wearable_priority_feedback.py`
- [X] T014 [P] [US1] Add integration coverage for Arabic startup, onboarding, interrupt, and offline prompt localization in `tests/integration/test_runtime_prompt_localization.py`
- [X] T015 [P] [US1] Add smoke regression for Arabic first-run setup readability in `tests/smoke/test_runtime_quickstart.py`

### Implementation for User Story 1

- [X] T016 [US1] Route startup readiness, degraded startup, and offline safe-refusal guidance through approved prompt keys in `core/assistant_runtime.py`
- [X] T017 [US1] Route onboarding intro, language, voice, speed, name, and onboarding confirmation prompts through approved prompt keys in `core/assistant_runtime.py`
- [X] T018 [US1] Replace embedded interrupt acknowledgement texts with catalog-backed prompt resolution in `core/assistant_runtime.py` and `settings/settings_manager.py`
- [X] T019 [US1] Emit same-language emergency fallback text and runtime integrity-failure signals for corrupted critical prompts in `settings/settings_manager.py` and `core/assistant_runtime.py`
- [X] T020 [US1] Run US1 validation (`python -m pytest tests/unit/test_settings_critical_prompt_catalog.py tests/integration/test_runtime_prompt_localization.py tests/smoke/test_runtime_quickstart.py -q`) and record SC-001/SC-002/SC-006 evidence in `specs/007-localization-prompt-hardening/quickstart.md`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Keep Critical Prompts Consistent Everywhere (Priority: P2)

**Goal**: Enforce one approved source of truth so critical runtime surfaces resolve through stable prompt keys rather than embedded text.

**Independent Test**: Exercise protected-command and runtime critical flows and verify every critical surface resolves through approved prompt keys with no embedded-text drift.

### Tests for User Story 2

- [X] T021 [P] [US2] Add unit coverage for prompt-key uniqueness, required language pairs, and surface-binding completeness in `tests/unit/test_settings_critical_prompt_catalog.py` and `tests/unit/test_release_localization_integrity.py`
- [X] T022 [P] [US2] Add integration coverage for protected-command confirmation localization and cross-surface prompt consistency in `tests/integration/test_command_confirmation_localization.py` and `tests/integration/test_runtime_prompt_localization.py`

### Implementation for User Story 2

- [X] T023 [US2] Expand the approved critical prompt catalog and surface map for startup, onboarding, interrupt, offline, and protected-command families in `core/critical_prompts.py` and `settings/settings_manager.py`
- [X] T024 [P] [US2] Route protected-command confirmation prompts through approved prompt keys in `core/resolver.py`
- [X] T025 [P] [US2] Replace remaining embedded critical prompt text in controller/runtime helpers with surface-bound catalog lookups in `controllers/mock_controllers.py`
- [X] T026 [US2] Persist surface-binding metadata and remove bypass paths for critical prompt resolution in `settings/settings_manager.py`, `core/assistant_runtime.py`, and `core/resolver.py`
- [X] T027 [US2] Update prompt catalog documentation and operator troubleshooting for bound critical surfaces in `specs/007-localization-prompt-hardening/contracts/critical-prompt-catalog-contract.md` and `docs/release/troubleshooting.md`
- [X] T028 [US2] Run US2 validation (`python -m pytest tests/integration/test_runtime_prompt_localization.py tests/integration/test_command_confirmation_localization.py -q`) and record SC-005 evidence in `specs/007-localization-prompt-hardening/quickstart.md`

**Checkpoint**: User Stories 1 and 2 are independently functional and testable.

---

## Phase 5: User Story 3 - Block Broken Localization Before Release (Priority: P3)

**Goal**: Expand release localization validation so candidate builds fail deterministically on corrupted prompt content or unapproved critical-surface bindings.

**Independent Test**: Run release localization validation and confirm it fails on empty text, replacement characters, mojibake patterns, language mismatches, unapproved surfaces, and embedded critical text while reporting `prompt_key` and `surface_id`.

### Tests for User Story 3

- [X] T029 [P] [US3] Extend unit coverage for failure-reason classification and blocking findings in `tests/unit/test_release_localization_integrity.py`
- [X] T030 [P] [US3] Extend integration coverage for catalog-plus-surface localization validation results in `tests/integration/test_release_localization_validation.py`
- [X] T031 [P] [US3] Add release-pipeline regression coverage for localization gate blocking and evidence fields in `tests/integration/test_release_workflow.py`

### Implementation for User Story 3

- [X] T032 [US3] Implement deterministic Arabic mojibake, replacement-character, missing-text, and language-mismatch detection in `core/release_localization.py`
- [X] T033 [US3] Implement two-pass validation for catalog entries and critical surface bindings in `core/release_localization.py` and `core/release_gates.py`
- [X] T034 [US3] Serialize `prompt_key`, `surface_id`, `catalog_source`, and failure-reason evidence in `core/release_localization.py` and `core/release_artifacts.py`
- [X] T035 [US3] Update release validation contract and checklist guidance for localization blocking criteria in `specs/007-localization-prompt-hardening/contracts/localization-validation-contract.md` and `docs/release/checklist.md`
- [X] T036 [US3] Run US3 validation (`python -m pytest tests/unit/test_release_localization_integrity.py tests/integration/test_release_localization_validation.py tests/integration/test_release_workflow.py -q`) and record SC-003/SC-004 evidence in `specs/007-localization-prompt-hardening/quickstart.md`

**Checkpoint**: All user stories are independently functional and testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup, edge-case coverage, and full validation across stories.

- [X] T037 [P] Refresh localization troubleshooting and validation steps for operators in `docs/release/troubleshooting.md` and `specs/007-localization-prompt-hardening/quickstart.md`
- [X] T038 Refactor duplicated critical prompt constants and dead fallback text in `core/assistant_runtime.py`, `core/resolver.py`, `controllers/mock_controllers.py`, and `settings/settings_manager.py`
- [X] T039 [P] Add edge-case regression coverage for missing prompt keys, embedded-text bypass, and same-language emergency fallback signaling in `tests/unit/test_settings_critical_prompt_catalog.py`, `tests/integration/test_runtime_prompt_localization.py`, and `tests/integration/test_release_localization_validation.py`
- [X] T040 Run full validation sweep (`python -m pytest tests/unit/test_settings_critical_prompt_catalog.py tests/unit/test_release_localization_integrity.py -q`, `python -m pytest tests/integration/test_runtime_prompt_localization.py tests/integration/test_command_confirmation_localization.py tests/integration/test_release_localization_validation.py tests/integration/test_release_workflow.py -q`, `python -m pytest tests/smoke/test_runtime_quickstart.py -q`) and record outputs in `specs/007-localization-prompt-hardening/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories
- **User Stories (Phases 3-5)**: Depend on Foundational completion
- **Polish (Phase 6)**: Depends on completion of user stories selected for release scope

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on other stories
- **US2 (P2)**: Starts after Foundational; uses the shared catalog and surface registry but remains independently testable
- **US3 (P3)**: Starts after Foundational; final full-surface release validation should run after US2 completes the critical surface inventory

### Within Each User Story

- Write listed tests first and confirm they fail before implementation
- Update shared prompt catalog and surface bindings before wiring runtime call sites
- Run the listed validation command and record evidence in `specs/007-localization-prompt-hardening/quickstart.md` before marking the story complete

### Parallel Opportunities

- `T002`, `T003`, and `T004` can run in parallel after `T001`
- `T006` and `T007` can run in parallel during Foundational work
- `T013`, `T014`, and `T015` can run in parallel for US1
- `T021` and `T022` can run in parallel for US2
- `T024` and `T025` can run in parallel after `T023`
- `T029`, `T030`, and `T031` can run in parallel for US3
- `T037` and `T039` can run in parallel during Polish

---

## Parallel Example: User Story 1

```bash
Task: "Add unit coverage for readable prompt selection and runtime fallback repair paths in tests/unit/test_settings_critical_prompt_catalog.py and tests/unit/test_wearable_priority_feedback.py"
Task: "Add integration coverage for Arabic startup, onboarding, interrupt, and offline prompt localization in tests/integration/test_runtime_prompt_localization.py"
Task: "Add smoke regression for Arabic first-run setup readability in tests/smoke/test_runtime_quickstart.py"
```

## Parallel Example: User Story 2

```bash
Task: "Route protected-command confirmation prompts through approved prompt keys in core/resolver.py"
Task: "Replace remaining embedded critical prompt text in controller/runtime helpers with surface-bound catalog lookups in controllers/mock_controllers.py"
```

## Parallel Example: User Story 3

```bash
Task: "Extend unit coverage for failure-reason classification and blocking findings in tests/unit/test_release_localization_integrity.py"
Task: "Extend integration coverage for catalog-plus-surface localization validation results in tests/integration/test_release_localization_validation.py"
Task: "Add release-pipeline regression coverage for localization gate blocking and evidence fields in tests/integration/test_release_workflow.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate Arabic startup/onboarding/offline/interrupt readability before widening scope

### Incremental Delivery

1. Setup + Foundational establish shared prompt catalog, surface bindings, and integrity primitives
2. Deliver US1 for readable Arabic guidance with same-language fallback
3. Deliver US2 for catalog consistency and embedded-text removal across critical surfaces
4. Deliver US3 for deterministic release blocking and evidence output
5. Finish with Phase 6 polish and full validation sweep

### Parallel Team Strategy

1. Team aligns on Setup and Foundational together
2. After Phase 2:
   - Developer A: US1 runtime/onboarding readability flows
   - Developer B: US2 catalog consistency and confirmation/controller bindings
   - Developer C: US3 release localization validation and evidence reporting
3. Rejoin for cross-cutting cleanup and final validation

---

## Notes

- `[P]` tasks are parallel-safe only after their dependency prerequisites are complete
- Every user story includes explicit test tasks because this feature touches constitution-protected runtime and safety-critical release-gate behavior
- Keep `settings/user_profile.json` as the runtime baseline source of truth throughout implementation
- Preserve same-language emergency fallback behavior for every critical prompt surface

