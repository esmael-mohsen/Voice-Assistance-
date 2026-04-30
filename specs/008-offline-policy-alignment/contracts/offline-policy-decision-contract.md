# Offline Policy Decision Contract

## Purpose

Define the structured input and output payloads for startup and command-level
offline policy decisions in Phase 8.

## Offline Policy Evaluation Input Contract

```json
{
  "flow": "command",
  "capability_id": "ocr",
  "provider_id": "legacy",
  "override_mode": "auto",
  "detected_status": "offline",
  "effective_network_available": false,
  "provider_availability": "ready",
  "requires_network": true,
  "offline_allowlist": ["system_status"]
}
```

### Rules

- `flow` must be `startup` or `command`.
- `provider_availability` must remain separate from
  `effective_network_available`.
- `offline_allowlist` is authoritative only for explicitly approved
  capabilities.

## Offline Policy Decision Output Contract

```json
{
  "capability_id": "ocr",
  "provider_id": "legacy",
  "override_mode": "auto",
  "detected_status": "offline",
  "effective_network_available": false,
  "provider_availability": "ready",
  "requires_network": true,
  "offline_allowlisted": false,
  "decision": "safe_refusal",
  "error_code": "offline_not_allowlisted",
  "spoken_surface_id": "runtime.offline.safe_refusal",
  "spoken_text": "Network unavailable. Try again when connected."
}
```

### Rules

- `decision` must be one of:
  `allow_execution`, `on_device_fallback`, `safe_refusal`,
  `provider_degraded`, or `offline_startup`.
- `safe_refusal`, `provider_degraded`, and `offline_startup` require
  `error_code`, `spoken_surface_id`, and `spoken_text`.
- `on_device_fallback` requires `offline_allowlisted=true`.
- `allow_execution` is invalid when `requires_network=true`,
  `effective_network_available=false`, and no approved fallback exists.
- Legacy payloads may include `network_available` as an alias of
  `effective_network_available` for backward compatibility.

## Startup Readiness Payload Contract

```json
{
  "startup_status": "degraded",
  "provider_id": "legacy",
  "requires_network": true,
  "effective_network_available": false,
  "provider_availability": "ready",
  "degraded_reason": "network_required_provider_offline",
  "spoken_surface_id": "runtime.startup.degraded"
}
```

### Rules

- A provider that requires network must not emit `startup_status=ready` when
  `effective_network_available=false`.
- Startup guidance must use approved critical prompt surfaces.
- Provider unavailability and network unavailability may share an offline-safe
  outcome, but they must remain distinguishable in diagnostics.

## Required Observability Fields

Offline-policy diagnostics should include these keys when available:

- `flow`
- `capability_id`
- `provider_id`
- `override_mode`
- `detected_status`
- `effective_network_available`
- `provider_availability`
- `requires_network`
- `offline_allowlisted`
- `decision`
- `error_code`

## Validation Expectations

- Unit tests for pure decision outcomes and error-code selection.
- Integration tests for runtime safe-refusal, allowlisted fallback, and startup
  degraded/offline readiness behavior.
- Smoke coverage for provider-by-provider offline truthfulness in console or
  headless-first mode.
