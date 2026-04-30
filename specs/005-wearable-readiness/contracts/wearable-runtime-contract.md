# Wearable Runtime Contract

## Purpose

Define runtime-facing behavior for wearable readiness: priority routing,
interruptible and bounded speech sessions, wake policy, degraded/offline
handling, and startup readiness signaling.

## Runtime Priority Event Contract

Every user-visible runtime output event should normalize to:

```json
{
  "event_id": "evt-001",
  "priority": "warning",
  "message_text": "Obstacle ahead.",
  "message_key": "obstacle_warning",
  "created_at": "2026-04-18T15:00:00Z",
  "coalescing_group": "obstacle_warning_front",
  "source": "runtime",
  "requires_immediate_delivery": true
}
```

### Rules

- Allowed priority values: `warning`, `action_confirmation`, `info`, `error`.
- Higher priority must be delivered before lower priority when events compete.
- Same-priority duplicates in the same `coalescing_group` must coalesce within
  a 2-second window.
- Runtime assistant events include `coalesced` and `coalescing_window_s` for
  observability.

## Speech Session Contract

Listening and speaking windows should normalize to:

```json
{
  "session_window_id": "sw-101",
  "mode": "speaking",
  "started_at": "2026-04-18T15:00:05Z",
  "max_duration_s": 6.0,
  "interrupted": false,
  "interrupt_reason": "none",
  "completion_status": "success"
}
```

### Rules

- Every session requires a positive `max_duration_s`.
- Timeout must produce `completion_status: "timeout"` and a recoverable
  machine-readable outcome.
- Active session must remain preemptible by high-priority interruption intents.

## Interruption Contract

High-priority interruption signal:

```json
{
  "signal_id": "sig-050",
  "signal_type": "stop",
  "issued_at": "2026-04-18T15:00:06Z",
  "source": "voice",
  "target_window_id": "sw-101"
}
```

### Rules

- Allowed signal types: `stop`, `cancel`, `emergency`.
- Preemption target: <= 1 second in at least 95% of validation attempts.
- Interrupted non-critical speech must be discarded and not auto-resumed unless
  the user explicitly re-requests it.

## Wake Strategy Contract

Wake policy state:

```json
{
  "primary_mode": "keyword_low_power",
  "fallback_mode": "hardware_trigger",
  "dev_fallback_mode": "stt_based_wake",
  "stt_wake_allowed_in_production": false
}
```

### Rules

- Production default must be low-power keyword wake.
- Hardware trigger is fallback when keyword wake is unavailable or fails.
- STT-based wake remains development-only fallback.

## Offline/Degraded Handling Contract

Execution decision shape:

```json
{
  "capability_id": "ocr",
  "provider_id": "speakkit",
  "requires_network": true,
  "offline_allowlisted": false,
  "decision": "safe_refusal",
  "offline_policy_decision": "safe_refusal",
  "spoken_text": "Network unavailable. Try again when connected."
}
```

### Rules

- `requires_network=true` actions must not run offline unless explicitly
  allowlisted for on-device fallback.
- Non-allowlisted offline actions must safe-refuse with short guidance.
- Risky fuzzy execution is prohibited when offline policy denies execution.

## Startup Readiness Contract

Startup readiness event:

```json
{
  "session_id": "sess-abc",
  "startup_status": "ready",
  "startup_latency_ms": 1200,
  "degraded_reason": null,
  "cue_id": "tone_ready",
  "cue_state": "ready",
  "wake_mode": "keyword_low_power",
  "wake_fallback_mode": "hardware_trigger",
  "wake_dev_fallback_mode": "stt_based_wake"
}
```

### Rules

- Non-visual readiness should be reached within 8 seconds in >=95% of boots.
- Startup status must be explicit: `initializing`, `ready`, `degraded`, or
  `offline`.

## Runtime Recovery Outcome Contract

Recovery outcome:

```json
{
  "recovery_trigger": "interrupt",
  "status": "recovered",
  "spoken_text": "Stopped.",
  "error_code": "interrupt_applied",
  "duration_ms": 380,
  "next_state": "standby",
  "completion_status": "interrupted",
  "interrupt_signal_type": "stop",
  "preemption_latency_ms": 380
}
```

### Rules

- `spoken_text` is always required and should stay concise.
- Non-success/degraded outcomes must include a stable `error_code`.
- Recovery outcomes must be machine-readable for observability and tests.

## Observability Fields

Runtime events should include these keys when relevant:

- `priority`
- `coalesced`
- `coalescing_window_s`
- `interrupt_signal_type`
- `session_mode`
- `completion_status`
- `requires_network`
- `offline_policy_decision`
- `startup_status`
- `startup_latency_ms`
- `cue_id`
- `cue_state`
- `dispatch_duration_ms`

## Validation Expectations

- Unit coverage for priority routing, coalescing, interruption, and offline
  decisions.
- Integration coverage for runtime state transitions and recovery outcomes in
  console and GUI-bridge paths.
- Smoke validation for startup/standby readiness and degraded behavior.
