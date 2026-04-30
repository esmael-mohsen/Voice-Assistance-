# Hybrid Command Recognition Contract

## Purpose

Define the machine-readable recognition result emitted after local-first decode
and any bounded rescue behavior.

## Output Shape

```json
{
  "session_id": "session-42",
  "capture_attempt_id": "cap-42",
  "recognition_path": "local_first",
  "provider_id": "legacy_vosk",
  "profile_id": "command.default",
  "primary_transcript": "read text",
  "alternative_transcripts": [
    "read text",
    "read the text"
  ],
  "confidence_score": 0.88,
  "confidence_available": true,
  "detected_language": "en-US",
  "language_candidates": [
    "en-US",
    "ar-EG"
  ],
  "latency_ms": 820,
  "dictionary_bias_applied": true,
  "closed_vocabulary_id": null,
  "endpoint_quality_hints": [],
  "error_code": null
}
```

## Rules

- `recognition_path` must be `local_first` or `rescue`.
- Runtime compatibility note: legacy payloads may still emit `fallback`; treat
  it as equivalent to `rescue` during transition.
- `primary_transcript` is required for successful recognition results.
- `confidence_available=false` requires `confidence_score=null`.
- `dictionary_bias_applied=true` requires an active capture profile that
  enables command-inventory or closed-choice bias.
- `closed_vocabulary_id` is required only for constrained modes.
- `endpoint_quality_hints` should summarize capture quality observations that
  may affect runtime decisions.

## Required Observability Fields

- `session_id`
- `capture_attempt_id`
- `recognition_path`
- `provider_id`
- `profile_id`
- `primary_transcript`
- `confidence_available`
- `confidence_score`
- `alternative_transcripts`
- `detected_language`
- `language_candidates`
- `latency_ms`
- `dictionary_bias_applied`
- `closed_vocabulary_id`
- `endpoint_quality_hints`
- `error_code`

## Validation Expectations

- Unit coverage for local-first, rescue, and constrained-mode result shaping.
- Integration coverage for rescue escalation, disagreement handling, and
  degraded-mode truthfulness.
- Smoke validation proving supported commands still complete through the
  local-first path when rescue is unnecessary.
