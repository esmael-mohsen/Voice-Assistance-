# Wake Mode Selection Contract

## Purpose

Define the machine-readable payload used when runtime standby selects the wake
mode for the current session.

## Input Shape

```json
{
  "wake_primary_mode": "keyword_low_power",
  "wake_fallback_mode": "hardware_trigger",
  "wake_dev_fallback_mode": "stt_based_wake",
  "stt_wake_allowed_in_production": false,
  "low_power_standby_enabled": true,
  "runtime_environment": "production_like",
  "keyword_wake_available": true,
  "hardware_trigger_available": true,
  "stt_wake_available": true,
  "provider_availability": "ready"
}
```

## Output Shape

```json
{
  "selected_mode": "keyword_low_power",
  "fallback_mode": "hardware_trigger",
  "dev_fallback_mode": "stt_based_wake",
  "selection_source": "configured",
  "fallback_reason": null,
  "degraded_mode": false,
  "degraded_reason": null
}
```

## Rules

- `selected_mode` must be one of:
  `keyword_low_power`, `hardware_trigger`, or `stt_based_wake`.
- `stt_based_wake` must not be selected in `production_like` mode when
  `stt_wake_allowed_in_production=false`.
- `selection_source=dev_fallback` requires `selected_mode=stt_based_wake`.
- `degraded_mode=true` requires a non-empty `degraded_reason`.
- If no permitted wake source is available, the result must reflect degraded
  standby rather than silently selecting a forbidden fallback.

## Required Observability Fields

- `selected_mode`
- `fallback_mode`
- `dev_fallback_mode`
- `selection_source`
- `fallback_reason`
- `degraded_mode`
- `degraded_reason`

## Validation Expectations

- Unit coverage for production-like rejection of STT wake.
- Unit coverage for development-only STT fallback selection.
- Integration coverage for unavailable wake-source degraded decisions.
