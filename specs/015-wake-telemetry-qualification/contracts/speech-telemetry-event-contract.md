# Speech Telemetry Event Contract

## Purpose

Define the lightweight structured telemetry payload used for live, replay, and
qualification speech events.

## Output Shape

```json
{
  "event_id": "evt-42",
  "scenario_label": "noisy-wake-cycle",
  "event_type": "wake_to_listen_latency",
  "session_id": "session-15",
  "interaction_id": "interaction-3",
  "timestamp_ms": 1760000012,
  "event_source": "assistant_runtime",
  "outcome_status": "within_target",
  "latency_ms": 930,
  "metric_value": 930,
  "evidence_scope": "qualification",
  "persisted_locally": true,
  "external_sink_status": "not_configured",
  "payload": {
    "wake_mode": "keyword_low_power",
    "prompt_class": "wake_ready",
    "provider_id": "legacy_wake",
    "artifact_bucket": "artifacts/run-15/speech"
  }
}
```

## Rules

- `event_type` must be one of the approved Phase 15 telemetry event types:
  `wake_accepted`, `wake_rejected`, `false_accept_review`,
  `false_reject_review`, `command_confidence_distribution`,
  `clarification_loop`, `prompt_echo_suppressed`, `clipped_retry`,
  `wake_to_listen_latency`, `listen_to_result_latency`,
  `result_to_speech_start_latency`, or `recovery_reset`.
- Latency event types require `latency_ms` and `metric_value`.
- `command_confidence_distribution` events must carry summary buckets,
  histogram data, or equivalent aggregate confidence metadata in `payload`.
- `persisted_locally=true` is required for default qualification evidence.
- `external_sink_status=failed` must not invalidate the local event when
  `persisted_locally=true`.
- `outcome_status` must describe the measured or decision result, not free-form
  operator commentary.

## Required Observability Fields

- `event_id`
- `scenario_label`
- `event_type`
- `session_id`
- `interaction_id`
- `timestamp_ms`
- `event_source`
- `outcome_status`
- `latency_ms`
- `metric_value`
- `evidence_scope`
- `persisted_locally`
- `external_sink_status`

## Validation Expectations

- Unit coverage for event shaping and validation across wake, latency, and
  recovery signals.
- Integration coverage for replay telemetry collection and sink-failure
  resilience.
- Qualification validation ensuring required events appear in the local
  evidence bundle.
