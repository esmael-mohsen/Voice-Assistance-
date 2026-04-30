# Failure Scenario Result Contract

## Purpose

Define the field-safe recovery result for covered STT failures.

## Result Shape

```json
{
  "scenario_id": "cloud-timeout-001",
  "failure_category": "cloud_timeout",
  "source": "google_cloud",
  "rollout_mode": "commands_low_risk",
  "bounded_outcome": "fallback",
  "crash_free": true,
  "spoken_guidance_surface": "runtime.stt.retry_or_fallback",
  "diagnostic_reason_code": "cloud_timeout_fallback",
  "field_safe_metadata": {
    "raw_audio_present": false,
    "raw_utterance_present": false,
    "latency_bucket": "threshold_breach"
  }
}
```

## Rules

- Every covered failure resolves to `fallback`, `retry`, `safe_refusal`, or
  `standby`.
- Passing scenarios must set `crash_free=true`.
- Missing fallback model scenarios must not crash and must use retry, safe
  refusal, or standby.
- Diagnostics must exclude raw audio and raw utterance content.

## Validation Expectations

- Unit tests cover failure-category mapping.
- Integration tests cover no network, missing credentials, expired
  credentials, quota/rate errors, cloud timeout, missing fallback, microphone
  timeout, repeated clipping, and language mismatch.
