# Speech Loop Recovery Contract

## Purpose

Define the structured runtime result emitted when the assistant recovers from
ordinary wake, STT, provider, or telemetry faults.

## Output Shape

```json
{
  "trigger": "speech_loop_recovery",
  "status": "recovered_to_standby",
  "spoken_text": "Let's try again. I'm back in standby.",
  "error_code": "ordinary_fault_budget_reached",
  "returned_state": "standby",
  "degraded_mode": false,
  "fault_sequence_count": 3,
  "last_fault_type": "stt_failure",
  "payload": {
    "provider_status": "degraded",
    "reset_triggered": true,
    "retry_allowed": false,
    "telemetry_recorded": true
  }
}
```

## Rules

- `status` must be one of:
  `retry_allowed`, `recovered_to_standby`, or `degraded_recovery`.
- `fault_sequence_count=3` requires `reset_triggered=true` and
  `returned_state=standby`.
- `telemetry_sink_fault` may produce recovery output but must not cause runtime
  exit.
- `degraded_recovery` requires `degraded_mode=true`.
- Recovery outputs must preserve truthful spoken guidance and safe state
  transitions.

## Required Observability Fields

- `trigger`
- `status`
- `spoken_text`
- `error_code`
- `returned_state`
- `degraded_mode`
- `fault_sequence_count`
- `last_fault_type`
- `payload.provider_status`
- `payload.reset_triggered`
- `payload.retry_allowed`
- `payload.telemetry_recorded`

## Validation Expectations

- Unit coverage for fault counting and reset behavior.
- Integration coverage for repeated wake or STT failures and provider timeout
  recovery.
- Smoke validation that ordinary faults never cause unexpected runtime exit.
