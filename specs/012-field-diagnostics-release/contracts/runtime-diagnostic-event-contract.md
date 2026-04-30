# Runtime Diagnostic Event Contract

## Purpose

Define the canonical field-safe diagnostic shape shared by provider-selection,
offline-policy, and interrupt runtime outcomes.

## Output Shape

```json
{
  "event_id": "diag-001",
  "timestamp": "2026-04-21T18:22:00Z",
  "session_or_run_id": "session-42",
  "event_category": "offline_policy",
  "status_or_decision": "refused",
  "reason_code": "network_required_offline",
  "provider_context": {
    "provider_id": "speakkit",
    "provider_availability": "degraded",
    "degraded_mode": true,
    "degraded_reason": "network_unavailable"
  },
  "next_state": "idle",
  "latency_ms": null,
  "user_outcome": "Assistant explained that the request cannot run offline.",
  "field_safe": true,
  "raw_user_content_present": false
}
```

## Rules

- `event_category` must be one of `provider_selection`, `offline_policy`, or
  `interrupt`.
- `field_safe=true` requires `raw_user_content_present=false`.
- `provider_context` must be present for provider-selection and offline-policy
  events and should remain available for interrupt events when provider state
  influenced the outcome.
- `latency_ms` must be included for interrupt events when preemption timing is
  measured.
- `degraded_mode=true` requires a non-empty `degraded_reason`.
- The default artifact set must not include raw user utterances.

## Required Observability Fields

- `event_id`
- `timestamp`
- `session_or_run_id`
- `event_category`
- `status_or_decision`
- `reason_code`
- `provider_context.provider_id`
- `provider_context.provider_availability`
- `provider_context.degraded_mode`
- `provider_context.degraded_reason`
- `next_state`
- `latency_ms`
- `field_safe`
- `raw_user_content_present`

## Validation Expectations

- Unit coverage for canonical-field validation and privacy defaults.
- Integration coverage for provider-selection, offline-policy, and interrupt
  scenarios emitting the same envelope.
- Parity validation showing headless and GUI paths preserve the same
  diagnostic meaning.
