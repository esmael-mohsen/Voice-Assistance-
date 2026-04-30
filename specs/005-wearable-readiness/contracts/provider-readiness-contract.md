# Provider Readiness Contract

## Purpose

Define provider metadata and policy decisions required to support wearable-safe
startup, wake behavior, and offline/degraded execution.

## Speech Provider Profile Shape

```json
{
  "provider_id": "speakkit",
  "display_name": "SpeakKit",
  "supports_wake": true,
  "supports_stt": true,
  "supports_tts": true,
  "requires_network": true,
  "availability": "ready",
  "startup_timeout_s": 5.0
}
```

### Rules

- `provider_id` must be normalized and unique in the provider registry.
- `startup_timeout_s` must be positive.
- `requires_network` must be accurate and treated as authoritative for offline
  policy.
- Availability must resolve to `ready`, `degraded`, or `unavailable`.

## Wake Capability Descriptor Shape

```json
{
  "provider_id": "legacy",
  "wake_modes_supported": [
    "keyword_low_power",
    "hardware_trigger",
    "stt_based_wake"
  ],
  "default_wake_mode": "keyword_low_power",
  "fallback_wake_mode": "hardware_trigger",
  "dev_only_wake_mode": "stt_based_wake"
}
```

### Rules

- Production default wake mode must be `keyword_low_power`.
- `stt_based_wake` must not be selected as production default.
- Fallback mode must remain available when primary wake degrades.

## Offline Execution Policy Shape

```json
{
  "capability_id": "system_status",
  "provider_id": "legacy",
  "requires_network": true,
  "offline_allowlisted": true,
  "decision": "on_device_fallback",
  "offline_policy_decision": "on_device_fallback",
  "error_code": "offline_allowlisted_fallback",
  "safe_refusal_prompt_key": null
}
```

### Rules

- If `requires_network=true` and `offline_allowlisted=false`, runtime must
  return safe refusal.
- If `offline_allowlisted=true`, runtime may execute on-device fallback only.
- Offline fallback must be explicit and command-scoped (allowlist), not
  inferred dynamically.
- Runtime policy decisions should use one of:
  `allow_execution`, `on_device_fallback`, `safe_refusal`.

## Startup Resolution Contract

Startup provider selection outcome:

```json
{
  "persisted_provider": "speakkit",
  "session_provider": "legacy",
  "selection_source": "startup_fallback",
  "degraded_mode": true,
  "degraded_reason": "provider_unavailable_at_startup",
  "offline_required": false
}
```

### Rules

- Startup resolution must always produce explicit source and degraded reason.
- If both primary and fallback providers are unavailable, `offline_required`
  must be `true` and runtime should enter safe offline state.

## Failure Resolution Contract

Runtime failure decision outcome:

```json
{
  "active_provider": "speakkit",
  "stage": "listening",
  "recoverable": true,
  "fallback_provider": "legacy",
  "fallback_applied": true,
  "next_state": "standby",
  "manual_restart_required": false,
  "reason_code": "speakkit_fallback_to_legacy"
}
```

### Rules

- Recoverable failures must define `next_state` explicitly.
- Fallback application must be explicit and logged.
- Unrecoverable failures must transition to safe offline state.

## Provider Observability Contract

At minimum, provider-related events should include:

- `provider_id`
- `availability`
- `requires_network`
- `selection_source`
- `degraded_mode`
- `degraded_reason`
- `fallback_applied`
- `reason_code`
- `offline_policy_decision`

## Validation Expectations

- Unit tests for startup and failure resolution behavior across provider
  availability combinations.
- Integration tests for provider switch behavior and deferred selection.
- Offline smoke checks to confirm allowlist policy and safe refusal behavior.
