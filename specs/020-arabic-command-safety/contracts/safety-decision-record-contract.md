# Safety Decision Record Contract

## Purpose

Define the machine-readable runtime decision that explains whether a command
was executed, confirmed, retried, refused, or routed through fallback after
canonicalization and parser evaluation.

## Confirm Shape

```json
{
  "decision_id": "decision-987",
  "intent_id": "stop_system",
  "decision_action": "confirm",
  "decision_band": "medium",
  "reason_code": "protected_confirmation_required",
  "confirmation_required": true,
  "retry_count": 0,
  "protected_command": true,
  "stable_supported_candidate": true,
  "spoken_guidance_surface": "resolver.confirmation.required",
  "field_safe_metadata": {
    "integrity_status": "trusted",
    "substitution_ids": ["ar.stop.waqef_al_nizam"],
    "confidence_band": "medium",
    "language_mismatch": false,
    "alternative_conflict": false
  },
  "payload": {
    "field_safe": true,
    "raw_user_content_present": false
  }
}
```

## Refuse Shape

```json
{
  "decision_id": "decision-988",
  "intent_id": null,
  "decision_action": "refuse",
  "decision_band": "missing_confidence",
  "reason_code": "corrupted_text_refusal",
  "confirmation_required": false,
  "retry_count": 1,
  "protected_command": false,
  "stable_supported_candidate": false,
  "spoken_guidance_surface": "runtime.command.refuse",
  "field_safe_metadata": {
    "integrity_status": "mojibake",
    "substitution_ids": [],
    "confidence_band": "missing_confidence",
    "language_mismatch": false,
    "alternative_conflict": false
  },
  "payload": {
    "field_safe": true,
    "raw_user_content_present": false
  }
}
```

## Rules

- Protected commands must not use `decision_action=execute` unless explicit
  confirmation has already been satisfied through the confirmation flow.
- `decision_action=confirm` requires `stable_supported_candidate=true`.
- Corrupted protected-command attempts must resolve to `refuse`, not `retry`
  into execution.
- Field-safe metadata must preserve the major safety inputs without exposing
  raw utterance content by default.

## Validation Expectations

- Unit tests cover execute, confirm, retry, refuse, and fallback paths across
  confidence bands and ambiguity conditions.
- Integration tests prove runtime command flows preserve the same safety
  expectations for cloud-primary and bounded fallback recognition outputs.
