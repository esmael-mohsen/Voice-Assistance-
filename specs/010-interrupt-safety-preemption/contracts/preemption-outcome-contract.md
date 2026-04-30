# Preemption Outcome Contract

## Purpose

Define the structured runtime outcome emitted after an accepted or ignored
interrupt path is resolved.

## Output Shape

```json
{
  "recovery_trigger": "interrupt",
  "status": "best_effort_only",
  "spoken_text": "Stopped.",
  "error_code": "interrupt_best_effort",
  "duration_ms": 120,
  "next_state": "standby",
  "completion_status": "partial",
  "interrupt_signal_type": "cancel",
  "preemption_latency_ms": 120,
  "capability_id": "face_recognition",
  "provider_id": "legacy",
  "matched_vocabulary_ids": ["interrupt-cancel-ar"],
  "cancellation_state": "best_effort_only",
  "follow_on_work_suppressed": true,
  "degraded_mode": true,
  "degraded_reason": "provider_stall",
  "runtime_load_profile": "moderate"
}
```

## Rules

- `recovery_trigger` must be `interrupt` for Phase 10 interrupt outcomes.
- `completion_status` must be one of:
  `interrupted`, `ignored`, `partial`, or `failed`.
- `next_state` must be a safe runtime state; the default successful target is
  `standby` unless a higher-priority safety recovery state is required.
- `partial` indicates speech was preempted but the underlying operation may
  already be completing.
- `preemption_latency_ms` is required for accepted interrupts and must be
  non-negative.
- Validation must fail any accepted interrupt path where
  `preemption_latency_ms > 1000`.

## Required Observability Fields

- `recovery_trigger`
- `status`
- `spoken_text`
- `error_code`
- `duration_ms`
- `next_state`
- `completion_status`
- `interrupt_signal_type`
- `preemption_latency_ms`
- `capability_id`
- `provider_id`
- `matched_vocabulary_ids`
- `cancellation_state`
- `follow_on_work_suppressed`
- `degraded_mode`
- `degraded_reason`
- `runtime_load_profile`

## Validation Expectations

- Integration coverage for accepted interrupt outcomes and safe next state.
- Latency assertions for accepted interrupts.
- Smoke validation for best-effort cancellation and no unintended follow-up
  speech after interruption.
