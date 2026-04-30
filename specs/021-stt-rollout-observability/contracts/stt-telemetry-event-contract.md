# STT Telemetry Event Contract

## Purpose

Define the field-safe event payload emitted for every covered recognition,
fallback, retry, clipping, timeout, Arabic-failure, or language-mismatch
outcome.

## Payload Shape

```json
{
  "event_id": "stt-event-001",
  "session_id": "session-123",
  "candidate_run_id": "candidate-2026-04-28",
  "event_type": "cloud_failure",
  "source": "google_cloud",
  "rollout_mode": "shadow",
  "status": "failed",
  "confidence_bucket": "missing",
  "failure_category": "cloud_timeout",
  "recovery_outcome": "fallback",
  "latency_bucket": "over_baseline",
  "reason_code": "cloud_timeout_strict_fallback",
  "field_safe": true,
  "raw_audio_present": false,
  "raw_utterance_present": false
}
```

## Required Enumerations

- `event_type`: `cloud_attempt`, `cloud_failure`, `strict_fallback`,
  `rescue_recognition`, `retry`, `clipping`, `timeout`, `arabic_failure`,
  `language_mismatch`, `confidence_policy`
- `source`: `google_cloud`, `strict_vosk`, `rescue`, `local`,
  `compatibility`, `none`
- `rollout_mode`: `shadow`, `wake_only`, `commands_low_risk`,
  `full_cloud_primary`, `rollback`
- `status`: `started`, `succeeded`, `failed`, `recovered`, `blocked`
- `confidence_bucket`: `high`, `medium`, `low`, `missing`, `unavailable`
- `failure_category`: `none`, `network`, `credentials`, `quota_or_rate`,
  `cloud_timeout`, `fallback_missing`, `microphone_timeout`, `clipping`,
  `language_mismatch`, `confidence_policy`, `unknown`
- `recovery_outcome`: `none`, `fallback`, `retry`, `safe_refusal`,
  `standby`
- `latency_bucket`: `within_target`, `baseline_regression`,
  `threshold_breach`, `over_baseline`, `unavailable`

## Rules

- Default telemetry must set `field_safe` to true.
- Default telemetry must set `raw_audio_present` and `raw_utterance_present`
  to false.
- Failed events require a non-`none` `failure_category` and a `reason_code`.
- Recovered events require a bounded `recovery_outcome`.
- Payloads must use reason codes and buckets only; they must not include raw
  transcripts, raw user utterances, audio paths, or credential material.

## Validation Expectations

- Unit tests validate required fields, enumerations, and privacy guards.
- Integration tests prove runtime diagnostics emit this shape for cloud,
  fallback, retry, clipping, timeout, Arabic failure, and language-mismatch
  paths.
