# STT Telemetry Rollup Contract

## Purpose

Define the field-safe aggregate payload used by release gates and field review
to understand STT behavior across a session or candidate run.

## Payload Shape

```json
{
  "rollup_id": "stt-rollup-001",
  "candidate_run_id": "candidate-2026-04-28",
  "session_count": 12,
  "event_count": 48,
  "rollout_mode_counts": {"shadow": 48},
  "source_counts": {"google_cloud": 20, "strict_vosk": 18, "rescue": 10},
  "status_counts": {"succeeded": 30, "failed": 8, "recovered": 10},
  "confidence_bucket_counts": {"high": 18, "medium": 9, "low": 3, "missing": 18},
  "failure_category_counts": {"credentials": 2, "cloud_timeout": 3, "language_mismatch": 3},
  "recovery_outcome_counts": {"fallback": 6, "retry": 2, "standby": 2},
  "latency_bucket_counts": {"within_target": 36, "threshold_breach": 2, "unavailable": 10},
  "fallback_frequency": 0.33,
  "cloud_failure_frequency": 0.25,
  "retry_rate": 0.04,
  "clipping_rate": 0.02,
  "timeout_rate": 0.06,
  "arabic_failure_count": 2,
  "language_mismatch_rate": 0.06,
  "field_safe": true,
  "retention_days": 180,
  "evidence_refs": ["artifacts/run-001/stt/rollup.json"]
}
```

## Rules

- Rollups must be derived from field-safe event records only.
- `retention_days` defaults to the existing 180-day release artifact policy.
- Missing telemetry must be represented as incomplete evidence, not silently
  omitted.
- Rollups must expose cloud failure frequency, strict fallback frequency or
  fallback frequency, rescue frequency when available, retry rate, clipping
  rate, timeout rate, Arabic failure count, language mismatch rate, confidence
  buckets, latency buckets, and reason-code summaries.
- Rollup payloads must not include raw audio, raw utterances, credentials, or
  full transcripts.

## Validation Expectations

- Unit tests validate aggregation math and privacy constraints.
- Integration tests prove release validation can consume rollups to block
  unsafe rollout evidence and approve complete safe evidence.
