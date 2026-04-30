# Confirmation Decision Contract

## Purpose

Define the structured confirmation outcome payload for protected commands in
Phase 9.

## Input Shape

```json
{
  "flow": "confirmation",
  "pending_intent_id": "stop_system",
  "raw_utterance": "yes please",
  "normalized_utterance": "yes please",
  "matched_outcomes": ["affirmative"]
}
```

## Output Shape

```json
{
  "validation_status": "ready",
  "error_code": null,
  "metadata": {
    "dialog_flow": "confirmation",
    "confirmation_response": "accepted",
    "dialog_normalized_utterance": "yes please",
    "dialog_matched_outcomes": ["affirmative"],
    "dialog_outcome": "affirmative",
    "dialog_safe_precedence_applied": false,
    "surface_id": "resolver.confirmation.required"
  }
}
```

## Rules

- `dialog_outcome` must be one of:
  `affirmative`, `negative`, `cancel`, `ambiguous`, `unmatched`.
- `confirmation_response` must be one of:
  `accepted`, `declined`, `retry_required`, `expired`.
- Protected execution is allowed only when:
  `validation_status=ready` and `dialog_outcome=affirmative`.
- Mixed cues must be non-executing and set
  `dialog_safe_precedence_applied=true`.
- Retry is bounded to one follow-up prompt; the next unresolved reply must end
  in `confirmation_expired`.

## Required Observability Fields

- `dialog_flow`
- `confirmation_response`
- `dialog_normalized_utterance`
- `dialog_matched_outcomes`
- `dialog_outcome`
- `dialog_safe_precedence_applied`
- `surface_id` when a critical prompt is spoken
- `error_code` for declined/expired outcomes

## Validation Expectations

- Unit tests for phrase-family matching, mixed-cue precedence, and unmatched
  noise.
- Integration tests for protected command execution, cancellation, and retry
  expiration.
- Smoke coverage for bilingual confirmation variants.
