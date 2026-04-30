# Tasks: Confirmation, Clarification, and Command Robustness

**Input**: Design documents from `/specs/009-confirmation-command-robustness/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are REQUIRED because this feature changes resolver behavior,
runtime dialog handling, critical prompt surfaces, and other safety-critical
confirmation and clarification flows.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g. `US1`, `US2`, `US3`)
- Include exact file paths in descriptions

## Path Conventions

- **Current project layout**: `main.py`, `controllers/`, `core/`, `settings/`, `tts/`, `ui/`, `tests/`, `docs/`
- **Feature focus**: shared dialog interpretation in `core/dialog_policy.py`, confirmation and clarification state in `core/command_models.py` and `core/resolver.py`, onboarding parity in `core/assistant_runtime.py`, prompt surfaces in `core/critical_prompts.py`, and regression coverage in `tests/unit/`, `tests/integration/`, and `tests/smoke/`
- **Specification docs**: `specs/009-confirmation-command-robustness/contracts/` and `specs/009-confirmation-command-robustness/quickstart.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare shared fixtures, regression modules, and validation evidence placeholders for Phase 9 work.

- [X] T001 Add dialog-state reset helpers and bilingual utterance fixtures in `tests/conftest.py`
- [X] T002 [P] Create Phase 9 unit and integration scaffolding in `tests/unit/test_dialog_confirmation_policy.py` and `tests/integration/test_command_dialog_robustness.py`
- [X] T003 [P] Create Phase 9 smoke scaffolding in `tests/smoke/test_confirmation_clarification_quickstart.py` and extend `tests/smoke/test_command_layer_quickstart.py`
- [X] T004 [P] Add Phase 9 validation evidence placeholders in `specs/009-confirmation-command-robustness/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared dialog-policy primitives, session state, and prompt contracts required by all user stories.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Add failing unit coverage for shared yes/no/cancel phrase parsing and safe precedence in `tests/unit/test_dialog_confirmation_policy.py` and `tests/unit/test_assistant_runtime.py`
- [X] T006 [P] Add failing integration coverage for confirmation, clarification, and stale follow-up transitions in `tests/integration/test_command_dispatch.py` and `tests/integration/test_command_dialog_robustness.py`
- [X] T007 [P] Add failing localization and onboarding-parity coverage in `tests/integration/test_command_confirmation_localization.py` and `tests/integration/test_runtime_modes.py`
- [X] T008 Define shared dialog interpretation and phrase-family normalization helpers in `core/dialog_policy.py`
- [X] T009 Extend session-context and structured dialog outcome models in `core/command_models.py`
- [X] T010 Add approved confirmation and clarification prompt surfaces in `core/critical_prompts.py`
- [X] T011 Add shared resolver and runtime metadata helpers for dialog outcomes in `core/resolver.py` and `core/assistant_runtime.py`

**Checkpoint**: Foundation ready; user story implementation can begin.

---

## Phase 3: User Story 1 - Safe Confirmation Matching (Priority: P1) MVP

**Goal**: Ensure protected commands recognize approved Arabic and English confirmation variants while remaining strictly non-executing for ambiguous or negative responses.

**Independent Test**: Trigger a protected command, respond with approved affirmative, negative, cancel, and mixed-cue variants, and verify execution happens only once after an explicit affirmative response.

### Tests for User Story 1

> **NOTE: Write these tests FIRST and ensure they fail before implementation
> because this story changes constitution-protected resolver and runtime
> behavior.**

- [X] T012 [P] [US1] Extend unit coverage for affirmative, negative, cancel, mixed-cue, and unmatched confirmation outcomes in `tests/unit/test_dialog_confirmation_policy.py` and `tests/unit/test_resolver.py`
- [X] T013 [P] [US1] Extend integration coverage for protected confirmation execution and cancellation flows in `tests/integration/test_command_dispatch.py` and `tests/integration/test_command_confirmation_localization.py`
- [X] T014 [P] [US1] Add smoke coverage for bilingual protected confirmation variants in `tests/smoke/test_command_layer_quickstart.py` and `tests/smoke/test_confirmation_clarification_quickstart.py`

### Implementation for User Story 1

- [X] T015 [US1] Replace exact-match protected confirmation parsing with shared dialog-policy decisions in `core/resolver.py` and `core/dialog_policy.py`
- [X] T016 [US1] Reuse the shared yes/no/cancel interpreter for comparable onboarding confirmation handling in `core/assistant_runtime.py`
- [X] T017 [US1] Preserve localized protected confirmation, decline, and safe-retry prompt behavior in `core/critical_prompts.py` and `core/resolver.py`
- [X] T018 [US1] Emit structured confirmation outcome fields and cancellation diagnostics in `core/resolver.py` and `core/command_models.py`
- [X] T019 [US1] Run US1 validation (`python -m pytest tests/unit/test_dialog_confirmation_policy.py tests/unit/test_resolver.py tests/integration/test_command_dispatch.py tests/integration/test_command_confirmation_localization.py tests/smoke/test_command_layer_quickstart.py tests/smoke/test_confirmation_clarification_quickstart.py -q`) and record SC-001, SC-002, and SC-003 evidence in `specs/009-confirmation-command-robustness/quickstart.md`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Bounded Clarification Prompts (Priority: P2)

**Goal**: Make parameter-required commands speak explicit supported options and stop safely after one initial prompt plus two retries.

**Independent Test**: Trigger `set language` or `set voice gender` without the required option, then verify valid answers resolve the command and repeated invalid answers stop safely without changing settings.

### Tests for User Story 2

- [X] T020 [P] [US2] Extend unit coverage for explicit supported-choice prompts, clarification resolution, and bounded retry counts in `tests/unit/test_resolver.py` and `tests/unit/test_dialog_confirmation_policy.py`
- [X] T021 [P] [US2] Add integration coverage for `set language` and `set voice gender` clarification flows plus safe-stop outcomes in `tests/integration/test_command_dispatch.py` and `tests/integration/test_command_dialog_robustness.py`
- [X] T022 [P] [US2] Extend smoke coverage for parameter-required clarification flows in `tests/smoke/test_command_layer_quickstart.py` and `tests/smoke/test_confirmation_clarification_quickstart.py`

### Implementation for User Story 2

- [X] T023 [US2] Implement explicit supported-option clarification prompts and three-attempt safe-stop behavior in `core/resolver.py` and `core/critical_prompts.py`
- [X] T024 [US2] Add clarification session tracking, retry bookkeeping, and structured failure outcomes in `core/command_models.py` and `core/resolver.py`
- [X] T025 [US2] Clear unrelated stale follow-up context when confirmation or clarification becomes active in `core/resolver.py` and `core/command_models.py`
- [X] T026 [US2] Keep clarification guidance in the active language across console, GUI, and headless runtime paths in `core/resolver.py` and `core/assistant_runtime.py`
- [X] T027 [US2] Run US2 validation (`python -m pytest tests/unit/test_resolver.py tests/unit/test_dialog_confirmation_policy.py tests/integration/test_command_dispatch.py tests/integration/test_command_dialog_robustness.py tests/smoke/test_command_layer_quickstart.py tests/smoke/test_confirmation_clarification_quickstart.py -q`) and record SC-004 evidence in `specs/009-confirmation-command-robustness/quickstart.md`

**Checkpoint**: User Stories 1 and 2 are independently functional and testable.

---

## Phase 5: User Story 3 - Reproducible Dialog Robustness (Priority: P3)

**Goal**: Provide deterministic regression coverage and observability for confirmation, clarification, and follow-up state interactions.

**Independent Test**: Run the dialog regression suite across Arabic and English variants, clarification retries, cancellations, onboarding reuse, and follow-up transitions, then verify outcomes and diagnostics remain deterministic.

### Tests for User Story 3

- [X] T028 [P] [US3] Extend unit regression coverage for follow-up isolation, shared interpreter parity, and structured dialog outcome payloads in `tests/unit/test_dialog_confirmation_policy.py`, `tests/unit/test_resolver.py`, and `tests/unit/test_assistant_runtime.py`
- [X] T029 [P] [US3] Extend integration coverage for overlapping confirmation, clarification, and follow-up transitions plus onboarding consistency in `tests/integration/test_command_dialog_robustness.py` and `tests/integration/test_runtime_modes.py`
- [X] T030 [P] [US3] Add smoke regression coverage for the full Phase 9 dialog quickstart in `tests/smoke/test_confirmation_clarification_quickstart.py`

### Implementation for User Story 3

- [X] T031 [US3] Emit deterministic dialog observability fields for confirmation, clarification, follow-up clearing, and safe-stop outcomes in `core/resolver.py`, `core/assistant_runtime.py`, and `core/command_models.py`
- [X] T032 [US3] Update Phase 9 dialog contracts and validation guidance to match shipped behavior in `specs/009-confirmation-command-robustness/contracts/confirmation-decision-contract.md`, `specs/009-confirmation-command-robustness/contracts/clarification-session-contract.md`, and `specs/009-confirmation-command-robustness/quickstart.md`
- [X] T033 [US3] Run US3 validation (`python -m pytest tests/unit/test_dialog_confirmation_policy.py tests/unit/test_resolver.py tests/unit/test_assistant_runtime.py tests/integration/test_command_dialog_robustness.py tests/integration/test_runtime_modes.py tests/smoke/test_confirmation_clarification_quickstart.py -q`) and record SC-005 evidence in `specs/009-confirmation-command-robustness/quickstart.md`

**Checkpoint**: All user stories are independently functional and testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup, localization integrity coverage, edge-case hardening, and full validation across all stories.

- [X] T034 [P] Refresh critical-prompt and localization-integrity regression coverage for new clarification surfaces in `tests/unit/test_settings_critical_prompt_catalog.py` and `tests/integration/test_runtime_prompt_localization.py`
- [X] T035 Remove stale exact-match confirmation helpers and dead one-retry clarification branches in `core/resolver.py` and `core/assistant_runtime.py`
- [X] T036 [P] Add edge-case regression coverage for mixed yes/cancel speech, mid-dialog language changes, background-noise safe retries, and stale-context reentry in `tests/unit/test_dialog_confirmation_policy.py`, `tests/integration/test_command_dialog_robustness.py`, and `tests/smoke/test_confirmation_clarification_quickstart.py`
- [X] T037 Run full validation sweep (`python -m pytest tests/unit/test_dialog_confirmation_policy.py tests/unit/test_resolver.py tests/unit/test_assistant_runtime.py tests/unit/test_settings_critical_prompt_catalog.py -q`, `python -m pytest tests/integration/test_command_dispatch.py tests/integration/test_command_confirmation_localization.py tests/integration/test_command_dialog_robustness.py tests/integration/test_runtime_modes.py tests/integration/test_runtime_prompt_localization.py -q`, `python -m pytest tests/smoke/test_command_layer_quickstart.py tests/smoke/test_confirmation_clarification_quickstart.py -q`, `python -m compileall core tests`) and record outputs in `specs/009-confirmation-command-robustness/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories
- **User Stories (Phases 3-5)**: Depend on Foundational completion
- **Polish (Phase 6)**: Depends on completion of the user stories selected for release scope

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on other stories
- **US2 (P2)**: Starts after Foundational; shares dialog primitives with US1 but remains independently testable
- **US3 (P3)**: Starts after Foundational; its full regression and documentation pass should run after US1 and US2 behavior is in place

### Within Each User Story

- Write listed tests first and confirm they fail before implementation
- Land shared model and prompt-surface updates before wiring runtime call sites
- Run the listed validation command and record evidence in `specs/009-confirmation-command-robustness/quickstart.md` before marking the story complete

### Parallel Opportunities

- `T002`, `T003`, and `T004` can run in parallel after `T001`
- `T006` and `T007` can run in parallel during Foundational work
- `T012`, `T013`, and `T014` can run in parallel for US1
- `T020`, `T021`, and `T022` can run in parallel for US2
- `T028`, `T029`, and `T030` can run in parallel for US3
- `T034` and `T036` can run in parallel during Polish

---

## Parallel Example: User Story 1

```bash
Task: "Extend unit coverage for affirmative, negative, cancel, mixed-cue, and unmatched confirmation outcomes in tests/unit/test_dialog_confirmation_policy.py and tests/unit/test_resolver.py"
Task: "Extend integration coverage for protected confirmation execution and cancellation flows in tests/integration/test_command_dispatch.py and tests/integration/test_command_confirmation_localization.py"
Task: "Add smoke coverage for bilingual protected confirmation variants in tests/smoke/test_command_layer_quickstart.py and tests/smoke/test_confirmation_clarification_quickstart.py"
```

## Parallel Example: User Story 2

```bash
Task: "Extend unit coverage for explicit supported-choice prompts, clarification resolution, and bounded retry counts in tests/unit/test_resolver.py and tests/unit/test_dialog_confirmation_policy.py"
Task: "Add integration coverage for set language and set voice gender clarification flows plus safe-stop outcomes in tests/integration/test_command_dispatch.py and tests/integration/test_command_dialog_robustness.py"
Task: "Extend smoke coverage for parameter-required clarification flows in tests/smoke/test_command_layer_quickstart.py and tests/smoke/test_confirmation_clarification_quickstart.py"
```

## Parallel Example: User Story 3

```bash
Task: "Extend unit regression coverage for follow-up isolation, shared interpreter parity, and structured dialog outcome payloads in tests/unit/test_dialog_confirmation_policy.py, tests/unit/test_resolver.py, and tests/unit/test_assistant_runtime.py"
Task: "Extend integration coverage for overlapping confirmation, clarification, and follow-up transitions plus onboarding consistency in tests/integration/test_command_dialog_robustness.py and tests/integration/test_runtime_modes.py"
Task: "Add smoke regression coverage for the full Phase 9 dialog quickstart in tests/smoke/test_confirmation_clarification_quickstart.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate protected confirmation safety and bilingual phrase-family behavior before widening scope

### Incremental Delivery

1. Setup + Foundational establish shared dialog-policy primitives, prompt surfaces, and session-state contracts
2. Deliver US1 for safe protected confirmation matching and onboarding confirmation reuse
3. Deliver US2 for explicit bounded clarification prompts and stale follow-up clearing
4. Deliver US3 for deterministic regression evidence and dialog observability
5. Finish with Phase 6 polish and full validation sweep

### Parallel Team Strategy

1. Team aligns on Setup and Foundational together
2. After Phase 2:
   - Developer A: US1 protected confirmation matching and onboarding parity
   - Developer B: US2 clarification prompts, retries, and follow-up isolation
   - Developer C: US3 regression matrix, observability, and validation evidence
3. Rejoin for cross-cutting cleanup and final validation

---

## Notes

- `[P]` tasks are parallel-safe only after their dependency prerequisites are complete
- Every user story includes explicit test tasks because this feature touches constitution-protected resolver, runtime, localization, and safety behavior
- Keep protected confirmation and clarification guidance routed through approved critical prompt surfaces rather than embedded one-off strings
- Phase 9 is intentionally limited to protected confirmations, comparable onboarding confirmation reuse, and parameter-required clarification flows
