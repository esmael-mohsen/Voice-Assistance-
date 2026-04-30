# Connectivity State Contract

## Purpose

Define the machine-readable provider truth, probe result, and effective
connectivity-state payloads used by runtime startup, offline policy evaluation,
and diagnostics for Phase 8.

## Provider Connectivity Profile Contract

```json
{
  "provider_id": "legacy",
  "display_name": "Legacy",
  "requires_network": true,
  "supports_wake": true,
  "supports_stt": true,
  "supports_tts": true,
  "fallback_provider_id": null
}
```

### Rules

- `requires_network` must reflect successful speech-path reality, not just
  wake-word or partial local availability.
- Provider identifiers must stay stable across settings, runtime, and tests.
- Any change to provider truth must be covered by provider registry tests.

## Network Probe Result Contract

```json
{
  "source": "background",
  "target_label": "tcp_primary",
  "status": "uncertain",
  "latency_ms": 850,
  "checked_at": "2026-04-20T10:15:00Z",
  "failure_reason": "timeout"
}
```

### Rules

- `status` must be one of `online`, `offline`, or `uncertain`.
- `failure_reason` is required when `status` is not `online`.
- `latency_ms` must be non-negative.

## Effective Connectivity State Contract

```json
{
  "override_mode": "auto",
  "detected_status": "uncertain",
  "effective_network_available": true,
  "last_confirmed_status": "online",
  "last_confirmed_at": "2026-04-20T10:14:58Z",
  "grace_window_active": true,
  "grace_window_deadline_at": "2026-04-20T10:15:00Z",
  "probe_generation": 7,
  "startup_reset_applied": true
}
```

### Rules

- Every startup must begin with `override_mode=auto`.
- `force_offline` and `force_online` may change
  `effective_network_available`, but must not erase `detected_status`.
- `grace_window_active=true` requires `detected_status=uncertain` and a
  non-null `grace_window_deadline_at`.
- When the grace deadline passes without confirmation, the next effective state
  must be offline-safe.

## Required Observability Fields

Connectivity and startup diagnostics should include these keys when available:

- `provider_id`
- `requires_network`
- `override_mode`
- `detected_status`
- `effective_network_available`
- `last_confirmed_status`
- `service_availability`
- `grace_window_active`
- `failure_reason`

## Validation Expectations

- Unit tests for provider metadata truth and connectivity-state transitions.
- Integration tests for startup reset and uncertainty grace handling.
- Smoke coverage showing startup guidance matches effective connectivity and
  provider truth.
