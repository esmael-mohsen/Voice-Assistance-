# Standby Wake Outcome Contract

## Purpose

Define the structured runtime outcome emitted after standby evaluates a wake
attempt through cloud-primary wake recognition, strict local fallback, or the
existing non-speech wake paths.

## Output Shape

```json
{
  "trigger": "wake_policy",
  "status": "wake_accepted",
  "spoken_text": "",
  "error_code": null,
  "next_runtime_state": "wake",
  "selected_wake_mode": "stt_based_wake",
  "attempt_source_mode": "stt_based_wake",
  "source_classification": "wake_strict_vosk_fallback",
  "canonical_wake_alias": "hi egb",
  "command_suffix_ignored": true,
  "payload": {
    "fallback_attempted": true,
    "fallback_used": true,
    "cloud_failure_reason": "cloud_network_timeout",
    "wake_to_listen_ms": 930,
    "field_safe": true,
    "raw_user_content_present": false
  }
}
```

## Status Values

- `wake_accepted`
- `wake_rejected`
- `wake_missed`
- `degraded_standby`

## Source Classification Values

- `cloud_primary`
- `wake_strict_vosk_fallback`
- `noncanonical_rejected`
- `keyword_low_power`
- `hardware_trigger`

## Rules

- `wake_accepted` requires `next_runtime_state` to advance to `wake` or
  `listening`.
- `wake_rejected` is used for non-canonical or otherwise disallowed wake
  attempts.
- `wake_missed` is used when cloud primary and strict local fallback both fail
  to produce a canonical wake.
- `command_suffix_ignored=true` means a canonical wake plus trailing text was
  accepted as wake-only and the trailing command text must not be executed or
  queued.
- `payload.field_safe` must remain `true` and
  `payload.raw_user_content_present` must remain `false` in default
  diagnostics.

## Validation Expectations

- Unit tests cover accepted, rejected, missed, and degraded outcomes.
- Integration tests cover cloud failure plus fallback success, non-canonical
  rejection, wake-plus-command safety, and repeated-miss standby recovery.
- Headless smoke validation proves the runtime stays understandable without GUI
  inspection.
