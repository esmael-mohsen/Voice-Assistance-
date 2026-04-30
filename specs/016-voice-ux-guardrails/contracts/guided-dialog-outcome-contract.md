# Guided Dialog Outcome Contract

## Purpose

Define the structured outcome produced after the assistant evaluates guided
input for onboarding, settings, confirmations, and short recovery flows.

## Output Shape

```json
{
  "trigger": "guided_dialog",
  "status": "retry_required",
  "spoken_text": "Please answer with one of the available options.",
  "error_code": "out_of_domain_answer",
  "next_runtime_state": "listening",
  "closed_vocabulary_id": "onboarding.language_choice",
  "payload": {
    "dialog_session_id": "guided-dialog-01",
    "accepted_option_id": null,
    "retry_count": 1,
    "retry_limit": 2,
    "prompt_echo_suppressed": false,
    "safe_default_applied": false,
    "graceful_exit": false,
    "preserved_safety_state": "guided_context_active"
  }
}
```

## Rules

- `status` must be one of:
  `accepted`, `retry_required`, `prompt_echo_suppressed`, `rejected`,
  `safe_default_applied`, or `graceful_exit`.
- `status=accepted` requires `payload.accepted_option_id` when a
  closed-vocabulary context is active.
- `status=prompt_echo_suppressed` must not increment the retry count by itself.
- `status=safe_default_applied` requires a safe fallback path for the current
  dialog field.
- `status=graceful_exit` is valid only when no safe continuation value exists.
- Unconfirmed or rejected name candidates must never be emitted as final
  accepted values.

## Required Observability Fields

- `trigger`
- `status`
- `spoken_text`
- `error_code`
- `next_runtime_state`
- `closed_vocabulary_id`
- `payload.dialog_session_id`
- `payload.accepted_option_id`
- `payload.retry_count`
- `payload.retry_limit`
- `payload.prompt_echo_suppressed`
- `payload.safe_default_applied`
- `payload.graceful_exit`
- `payload.preserved_safety_state`
- `payload.fallback_or_exit_reason`

## Validation Expectations

- Unit coverage for prompt-echo suppression, retry increments, safe-default
  continuation, and graceful exit.
- Integration coverage for mixed-language onboarding, out-of-domain rejection,
  protected-flow safety, and explicit name confirmation.
- Smoke validation for end-to-end guided dialog completion in headless mode.
