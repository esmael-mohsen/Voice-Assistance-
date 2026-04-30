# Confirmation Dialog Safety Contract

## Purpose

Define the multilingual confirmation turn used after a protected or medium-
risk command survives canonicalization and requires explicit user intent
confirmation.

## Accepted Shape

```json
{
  "turn_id": "confirm-100",
  "pending_intent_id": "reset_settings",
  "closed_vocabulary_id": "confirmation.yes_no",
  "prompt_surface_id": "resolver.confirmation.required",
  "accepted_language_scopes": ["english", "arabic", "bilingual"],
  "response_outcome": "affirmative",
  "safe_precedence_applied": false,
  "final_resolution": "execute"
}
```

## Safe-Decline Shape

```json
{
  "turn_id": "confirm-101",
  "pending_intent_id": "stop_system",
  "closed_vocabulary_id": "confirmation.yes_no",
  "prompt_surface_id": "resolver.confirmation.required",
  "accepted_language_scopes": ["english", "arabic", "bilingual"],
  "response_outcome": "cancel",
  "safe_precedence_applied": true,
  "final_resolution": "decline"
}
```

## Rules

- Protected-command confirmation must use the shared yes/no/cancel dialog
  interpretation path rather than parser-only intent matching.
- `final_resolution=execute` requires `response_outcome=affirmative`.
- Mixed replies may apply safe precedence when cancel or negative markers
  should outrank an affirmative marker.
- Confirmation handling must remain consistent across Arabic, English, and
  mixed-language replies.

## Validation Expectations

- Unit tests cover affirmative, negative, cancel, ambiguous, and unmatched
  responses in Arabic and English.
- Integration tests prove protected-command confirmation remains safe when the
  upstream transcript carried substitutions, language mismatch markers, or
  medium confidence.
