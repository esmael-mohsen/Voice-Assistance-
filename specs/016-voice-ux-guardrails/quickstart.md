# Quickstart: Continuous Turn-Taking, Closed-Vocabulary Guardrails, and Pilot-Grade Voice UX

## Goal

Validate that guided voice interactions feel natural without weakening safety:
allowed prompts should support early answers, protected flows should remain
strict, closed-vocabulary turns should reject unrelated speech cleanly,
prompt echo should not burn retry budget, uncertain names should never be
persisted without confirmation, and pilot UX evidence should stay structured
and field-safe.

## Preconditions

1. Use the project virtual environment and repository root.
2. Keep the active settings snapshot and prompt catalog consistent with the
   guided flows under test.
3. Prefer headless console validation first; use GUI checks only as a parity
   pass.
4. Keep local artifact output writable for pilot evidence bundles under
   `artifacts/<run-id>/`.
5. Prepare representative guided-dialog scenarios for onboarding, settings,
   confirmation, retry, prompt-echo suppression, and name confirmation.

## Validation Paths

### 1. Allowed Early Answers and Natural Barge-In

1. Exercise onboarding choices, low-risk settings, informational prompts, and
   retry/help prompts while answering before prompt completion.
2. Confirm the runtime captures the answer, shortens or stops prompt playback
   as needed, and advances without forcing a repeat.
3. Verify the resulting evidence records accepted barge-ins for the journey.

Expected outcome:
- Eligible prompts allow natural early answers.
- The runtime does not punish the user for answering during allowed playback.
- Pilot evidence records when early barge-in was accepted.

### 2. Protected Prompt Boundaries

1. Exercise confirmation, shutdown, and destructive flows while attempting to
   interrupt before the first protected prompt pass finishes.
2. Confirm the assistant preserves the protection boundary and only accepts
   input when the safe point is reached.

Expected outcome:
- Protected flows stay stricter than normal guided prompts.
- Safety prompts are not bypassed to improve responsiveness.

### 3. Closed-Vocabulary Resolution and Safe Rejection

1. Exercise language, voice, speed, yes/no/cancel, wake confirmation, and
   retry/help contexts with valid Arabic, English, and mixed aliases.
2. Exercise unrelated speech and non-safety commands during those contexts.
3. Confirm valid answers resolve, unsupported speech is rejected with a short
   recovery prompt, and only approved global safety commands preempt the flow.

Expected outcome:
- Closed-choice questions resolve quickly when the answer is valid.
- Unrelated speech stays inside the guided context unless it is a global
  safety command.
- Out-of-domain answers do not get over-interpreted as valid choices.

### 4. Prompt Echo Suppression and Retry Budget Control

1. Exercise scenarios where the assistant's own prompt text is captured by STT.
2. Confirm prompt echo is suppressed without consuming a retry by itself.
3. Exercise repeated invalid answers and confirm retries narrow in wording
   before safe fallback or graceful exit.

Expected outcome:
- Prompt echo no longer drives onboarding or settings loops.
- Retry budget reflects actual user-response failures, not self-capture.
- Final-retry behavior is bounded and understandable.

### 5. Name Capture, Confirmation, and Safe Fallback

1. Exercise clean name capture, clipped or noisy name capture, and explicit
   negative or cancel confirmations.
2. Confirm names become final only after explicit confirmation.
3. Confirm uncertain or rejected name candidates are discarded, while required
   setup choices continue with safe defaults when allowed.

Expected outcome:
- No uncertain name is persisted as final.
- Unconfirmed personalization is skipped safely when retry limits are reached.
- Required setup does not trap the user in indefinite retry loops.

### 6. Pilot UX Evidence Review

1. Run representative guided journeys for early answers, mixed-language
   onboarding, repeated invalid answers, prompt echo, and name confirmation
   recovery.
2. Review the local evidence bundle for completion status, retries used,
   accepted barge-ins, prompt-echo suppressions, out-of-domain rejections, and
   fallback or exit reason.

Expected outcome:
- Pilot evidence is easy to review without raw user utterances.
- Journey results map directly to the Phase 16 success criteria.

## Fixture Notes

- Guided-dialog fixture expectations live in `tests/fixtures/dialog/README.md`.
- Keep fixture definitions metadata-only and field-safe by default.
- If a scenario needs transcript-level debugging, use a temporary local-only
  debug fixture and remove raw utterance text before final evidence export.

## Validation Evidence Log

### SC-001

- Command: `python -m pytest tests/unit/test_turn_taking.py tests/unit/test_assistant_runtime.py tests/unit/test_tts_engine_interruptions.py tests/integration/test_command_recognition_runtime.py tests/integration/test_runtime_interruptions.py tests/integration/test_gui_runtime_bridge.py tests/smoke/test_runtime_quickstart.py -q`
- Result: `67 passed, 2 warnings in 20.59s` (executed 2026-04-23)
- Notes: Protected prompts remained blocked until safe handoff; eligible onboarding prompts accepted early-answer turns.

### SC-002 and SC-003

- Command: `python -m pytest tests/unit/test_closed_vocabulary.py tests/unit/test_dialog_confirmation_policy.py tests/unit/test_assistant_runtime.py tests/integration/test_closed_vocabulary_stt.py tests/integration/test_command_dialog_robustness.py tests/integration/test_runtime_failure_paths.py tests/smoke/test_runtime_quickstart.py -q`
- Result: `69 passed, 2 warnings in 18.95s` (executed 2026-04-23)
- Notes: Closed-vocabulary alias resolution, safe rejection, prompt-echo suppression, and global-safety preemption boundaries validated.

### SC-004 and SC-005

- Command: `python -m pytest tests/unit/test_assistant_runtime.py tests/unit/test_resolver.py tests/unit/test_runtime_contract.py tests/integration/test_command_dialog_robustness.py tests/integration/test_command_recognition_runtime.py tests/integration/test_release_journey_validation.py tests/smoke/test_runtime_quickstart.py -q`
- Result: `81 passed, 2 warnings in 17.82s` (executed 2026-04-23)
- Notes: Name-candidate confirmation and discard behavior validated; pilot voice UX summaries persisted with field-safe payloads only.

### Full Validation Sweep (T040)

- Unit sweep: `python -m pytest tests/unit/test_turn_taking.py tests/unit/test_closed_vocabulary.py tests/unit/test_dialog_confirmation_policy.py tests/unit/test_assistant_runtime.py tests/unit/test_resolver.py tests/unit/test_runtime_contract.py tests/unit/test_tts_engine_interruptions.py -q` -> `77 passed, 2 warnings in 13.07s`
- Integration sweep: `python -m pytest tests/integration/test_command_dialog_robustness.py tests/integration/test_closed_vocabulary_stt.py tests/integration/test_command_recognition_runtime.py tests/integration/test_runtime_interruptions.py tests/integration/test_runtime_failure_paths.py tests/integration/test_gui_runtime_bridge.py tests/integration/test_release_journey_validation.py -q` -> `29 passed, 2 warnings in 4.13s`
- Smoke sweep: `python -m pytest tests/smoke/test_runtime_quickstart.py -q` -> `14 passed, 2 warnings in 5.40s`
- Compile check: `python -m compileall core tests` -> success
- Lint check: `python -m ruff check .` -> `All checks passed!`

## Suggested Validation Commands

- `python -m pytest tests/unit/test_dialog_confirmation_policy.py tests/unit/test_resolver.py tests/unit/test_assistant_runtime.py -q`
- `python -m pytest tests/integration/test_command_dialog_robustness.py tests/integration/test_closed_vocabulary_stt.py tests/integration/test_command_recognition_runtime.py -q`
- `python -m pytest tests/integration/test_runtime_interruptions.py tests/integration/test_runtime_failure_paths.py tests/integration/test_gui_runtime_bridge.py -q`
- `python -m pytest tests/smoke/test_runtime_quickstart.py -q`
- `python -m compileall core tests`
- `ruff check .`

## Operator Notes

- Headless runtime remains the reference validation path for wearable voice UX.
- `core/critical_prompts.py` and the profile-backed prompt catalog remain the
  source of truth for guided spoken text.
- Only approved global safety commands should preempt a closed-vocabulary turn.
- Default pilot evidence must remain field-safe and exclude raw user utterances
  unless a separately approved fixture workflow is used.
