# Standby Wake Outcome Contract

## Purpose

Define the structured runtime outcome emitted when standby accepts, rejects, or
degrades a wake attempt.

## Output Shape

```json
{
  "trigger": "wake_policy",
  "status": "wake_rejected",
  "spoken_text": "Wake source unavailable. Waiting safely for recovery.",
  "error_code": "wake_source_unavailable",
  "next_runtime_state": "standby",
  "selected_wake_mode": "hardware_trigger",
  "attempt_source_mode": "stt_based_wake",
  "degraded_mode": true,
  "degraded_reason": "no_permitted_wake_source",
  "payload": {
    "runtime_environment": "production_like",
    "wake_cycle_locked": false,
    "degraded_guidance_announced": true,
    "wake_to_listen_ms": null,
    "listen_to_response_ms": null
  }
}
```

## Rules

- `status` must be one of:
  `wake_accepted`, `wake_rejected`, `degraded_standby`, or `unavailable`.
- `wake_accepted` requires `next_runtime_state` to advance to `wake` or
  `listening`.
- `wake_rejected` and `degraded_standby` must preserve a safe standby state.
- `degraded_guidance_announced=true` means unchanged degraded guidance must not
  be repeated again in the same standby entry.
- Accepted wake outcomes should include timing data when latency measurement is
  active.

## Required Observability Fields

- `trigger`
- `status`
- `spoken_text`
- `error_code`
- `next_runtime_state`
- `selected_wake_mode`
- `attempt_source_mode`
- `degraded_mode`
- `degraded_reason`
- `payload.runtime_environment`
- `payload.wake_cycle_locked`
- `payload.degraded_guidance_announced`

## Validation Expectations

- Integration coverage for production-like wake acceptance and STT rejection.
- Integration coverage for degraded standby with one-time guidance.
- Smoke validation for headless parity and first-valid-wins wake arbitration.
