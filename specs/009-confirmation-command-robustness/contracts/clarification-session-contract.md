# Clarification Session Contract

## Purpose

Define the structured clarification-state payload for parameter-required
commands in Phase 9 (`set_language`, `set_voice_gender`).

## Input Shape

```json
{
  "flow": "clarification",
  "intent_id": "set_language",
  "raw_utterance": "english",
  "attempt_count": 1,
  "max_attempts": 3
}
```

## Output Shape

```json
{
  "validation_status": "clarification_required",
  "error_code": "missing_required_parameter",
  "metadata": {
    "dialog_flow": "clarification",
    "clarification_attempt_count": 1,
    "clarification_remaining_attempts": 2,
    "surface_id": "resolver.clarification.language.required",
    "prompt_key": "clarification_language_required"
  }
}
```

## Rules

- Clarification is bounded to three total attempts:
  one initial prompt plus two retries.
- A valid supported option resolves the pending intent and sets
  `clarification_resolved=true`.
- Reaching max attempts must return
  `validation_status=failed` and `error_code=clarification_failed`.
- `cancel` or negative clarification replies must stop safely with
  `clarification_failed`.
- Starting confirmation or clarification must clear unrelated stale follow-up
  context.

## Required Observability Fields

- `dialog_flow`
- `clarification_attempt_count`
- `clarification_remaining_attempts`
- `clarification_resolved` when applicable
- `clarification_cancelled` when cancelled
- `surface_id`
- `prompt_key`
- `error_code`

## Validation Expectations

- Unit tests for option resolution, retry bounds, and terminal safe-stop.
- Integration tests for language/voice clarification and stale follow-up
  clearing.
- Smoke coverage for clarification resolve/fail quickstart paths.
