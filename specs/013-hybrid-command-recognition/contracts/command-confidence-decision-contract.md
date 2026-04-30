# Command Confidence Decision Contract

## Purpose

Define the runtime decision payload that explains whether a command was
executed, escalated to fallback, confirmed, retried, deferred, or refused.

## Output Shape

```json
{
  "intent_id": "stop_system",
  "decision_band": "low",
  "decision_action": "confirm",
  "protected_command": true,
  "fallback_attempted": true,
  "confirmation_required": true,
  "retry_count": 0,
  "spoken_guidance_surface": "resolver.confirmation.required",
  "reason_code": "protected_intent_low_confidence",
  "telemetry": {
    "session_id": "session-42",
    "recognition_path": "fallback",
    "confidence_band": "low",
    "fallback_used": true,
    "decision_outcome": "confirm",
    "protected_command": true,
    "latency_ms": 1820,
    "field_safe": true,
    "raw_utterance_present": false
  }
}
```

## Rules

- `decision_band` must be one of `high`, `medium`, `low`, or
  `missing_confidence`.
- `decision_action` must be one of `execute`, `fallback`, `confirm`, `retry`,
  `defer`, or `refuse`.
- Protected commands must never emit `decision_action=execute` below the safe
  protected-command threshold unless explicit affirmative confirmation has
  already been captured.
- `retry_count` must never exceed `1` for Phase 13.
- `fallback_attempted=true` requires evidence that fallback recognition was
  actually invoked.
- `telemetry.field_safe=true` requires `telemetry.raw_utterance_present=false`.

## Reason Code Examples

- `high_confidence`
- `missing_confidence_unprotected_allowed`
- `protected_confirmation_required`
- `fallback_required`
- `retry_required`
- `retry_exhausted`
- `fallback_unavailable`
- `offline_local_execute`
- `unparsed_forward_to_dispatch`

## Required Observability Fields

- `intent_id`
- `decision_band`
- `decision_action`
- `protected_command`
- `fallback_attempted`
- `confirmation_required`
- `retry_count`
- `spoken_guidance_surface`
- `reason_code`
- `telemetry.session_id`
- `telemetry.recognition_path`
- `telemetry.confidence_band`
- `telemetry.fallback_used`
- `telemetry.decision_outcome`
- `telemetry.latency_ms`

## Validation Expectations

- Unit coverage for high, medium, low, and missing-confidence decision rules.
- Integration coverage for fallback escalation, protected-command confirmation,
  and offline-safe refusal.
- Smoke validation proving command-recognition telemetry remains metadata-first
  while still explaining the decision path.
