# Quickstart: Confirmation, Clarification, and Command Robustness

## Goal

Validate resilient confirmation and clarification behavior in Arabic and
English without weakening protected-command safety or allowing stale follow-up
context to leak into the active dialog.

## Preconditions

1. Use the project virtual environment and repository root.
2. Reset pending confirmation, clarification, and follow-up session state
   between validation cases.
3. Exercise at least one protected command, one parameter-required settings
   intent, and one follow-up pair such as `recognize face` followed by
   `recognize emotion`.

## Validation Paths

### 1. Protected Confirmation Variants

1. Trigger a protected intent such as `stop system` or `reset settings`.
2. Respond with approved affirmative variants such as `yes`, `yes please`, and
   `aywa tamam`.
3. Repeat with explicit negative or cancel replies such as `no` and `cancel`.
4. Repeat with a mixed utterance containing both affirmative and cancel cues.

Expected outcome:
- Execution occurs only once after an explicit affirmative outcome.
- Negative and cancel replies clear the pending action and announce the
  cancellation.
- Mixed yes and cancel input resolves to the safe non-executing outcome.

### 2. Explicit Clarification Choices and Bounded Retries

1. Trigger a settings intent without its required parameter, such as
   `set language` or `set voice gender`.
2. Verify the clarification prompt speaks the currently supported choices
   explicitly.
3. Reply with a valid supported option and verify the command resolves.
4. Repeat with invalid or unrelated answers until the retry budget is exhausted.

Expected outcome:
- Supported options are spoken clearly in the active language.
- A valid supported choice resolves the pending command.
- The assistant stops safely after one initial prompt plus two retries and
  does not change settings on failure.

### 3. Follow-Up Isolation

1. Establish follow-up context through a command such as `recognize face`.
2. Before consuming that follow-up, trigger a protected confirmation or a
   parameter-required clarification flow.
3. Verify the stale follow-up state is cleared or ignored for the new dialog.
4. Confirm the new dialog can only be satisfied by the active confirmation or
   clarification input.

Expected outcome:
- Old follow-up context does not satisfy a confirmation or clarification turn.
- Confirmation, clarification, and follow-up state remain isolated and
  deterministic.

### 4. Suggested Validation Commands

- `python -m pytest tests/unit/test_resolver.py tests/unit/test_dialog_confirmation_policy.py -q`
- `python -m pytest tests/integration/test_command_dispatch.py tests/integration/test_command_confirmation_localization.py tests/integration/test_command_dialog_robustness.py -q`
- `python -m pytest tests/smoke/test_command_layer_quickstart.py tests/smoke/test_confirmation_clarification_quickstart.py -q`
- `python -m compileall core tests`

## Validation Evidence

Validation run date: **2026-04-20**

### User Story Validation Runs

- **US1 command**:
  `python -m pytest tests/unit/test_dialog_confirmation_policy.py tests/unit/test_resolver.py tests/integration/test_command_dispatch.py tests/integration/test_command_confirmation_localization.py tests/smoke/test_command_layer_quickstart.py tests/smoke/test_confirmation_clarification_quickstart.py -q`
  Result: **39 passed**
- **US2 command**:
  `python -m pytest tests/unit/test_resolver.py tests/unit/test_dialog_confirmation_policy.py tests/integration/test_command_dispatch.py tests/integration/test_command_dialog_robustness.py tests/smoke/test_command_layer_quickstart.py tests/smoke/test_confirmation_clarification_quickstart.py -q`
  Result: **41 passed**
- **US3 command**:
  `python -m pytest tests/unit/test_dialog_confirmation_policy.py tests/unit/test_resolver.py tests/unit/test_assistant_runtime.py tests/integration/test_command_dialog_robustness.py tests/integration/test_runtime_modes.py tests/smoke/test_confirmation_clarification_quickstart.py -q`
  Result: **57 passed**

### Full Sweep (Phase 6)

- Unit sweep:
  `python -m pytest tests/unit/test_dialog_confirmation_policy.py tests/unit/test_resolver.py tests/unit/test_assistant_runtime.py tests/unit/test_settings_critical_prompt_catalog.py -q`
  Result: **42 passed**
- Integration sweep:
  `python -m pytest tests/integration/test_command_dispatch.py tests/integration/test_command_confirmation_localization.py tests/integration/test_command_dialog_robustness.py tests/integration/test_runtime_modes.py tests/integration/test_runtime_prompt_localization.py -q`
  Result: **33 passed**
- Smoke sweep:
  `python -m pytest tests/smoke/test_command_layer_quickstart.py tests/smoke/test_confirmation_clarification_quickstart.py -q`
  Result: **9 passed**
- Compile check:
  `python -m compileall core tests`
  Result: **completed without errors**

### Success Criteria Mapping

- **SC-001** Protected intents remain blocked until explicit affirmative:
  covered by `test_dispatch_protected_command_confirmation_flow`,
  `test_bilingual_protected_confirmation_variants_execute_once`, and
  `test_resolver_requires_confirmation_for_protected_commands`.
- **SC-002** Approved bilingual phrase variants resolve correctly:
  covered by `test_dialog_policy_accepts_common_affirmative_variants`,
  `test_phase9_protected_confirmation_phrase_families_smoke`, and
  `test_runtime_modes_share_confirmation_phrase_policy`.
- **SC-003** Ambiguous/cancel paths remain non-executing:
  covered by `test_dispatch_confirmation_mixed_yes_cancel_stays_safe`,
  `test_dialog_policy_mixed_yes_and_cancel_prefers_safe_outcome`, and
  `test_background_noise_confirmation_retries_then_expires_safely`.
- **SC-004** Clarification resolves valid options or stops safely in bounds:
  covered by `test_dispatch_clarification_flow_fails_after_two_retries`,
  `test_parameter_clarification_resolves_or_stops_safely`, and
  `test_resolver_clarifies_with_explicit_options_then_fails_after_bounded_retries`.
- **SC-005** Shared yes/no/cancel outcomes stay consistent across flows:
  covered by `test_runtime_yes_interpreter_reuses_shared_dialog_policy` and
  `test_runtime_modes_share_confirmation_phrase_policy`.

## Operator Notes

- Keep dialog classification deterministic and local; protected confirmation is
  not a fuzzy-conversation feature.
- Negative and cancel precedence must remain stronger than affirmative matches
  when cues are mixed.
- Any confirmation or clarification prompt should continue to resolve through
  approved critical prompt surfaces instead of embedded one-off strings.
