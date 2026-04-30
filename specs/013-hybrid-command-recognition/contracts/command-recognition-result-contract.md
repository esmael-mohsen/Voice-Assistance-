# Command Recognition Result Contract

## Purpose

Define the machine-readable recognition result emitted by the command
recognition boundary before parser matching and runtime confidence decisions.

## Output Shape

```json
{
  "session_id": "session-42",
  "recognition_path": "local_first",
  "provider_id": "legacy",
  "primary_transcript": "read text",
  "confidence_score": 0.93,
  "confidence_available": true,
  "alternative_transcripts": [
    "read text",
    "read the text"
  ],
  "detected_language": "en-US",
  "latency_ms": 620,
  "error_code": null
}
```

## Rules

- `recognition_path` must be `local_first` or `fallback`.
- `primary_transcript` must be populated for successful recognition.
- `confidence_available=false` requires `confidence_score=null`.
- When a provider does not expose a native confidence score, implementations
  may keep `confidence_available=false` or emit a bounded estimated score with
  clear policy handling for missing-confidence safety.
- `alternative_transcripts` should preserve descending confidence or selection
  order when present.
- `latency_ms` must capture recognition duration for the specific path that
  produced this result.
- `error_code` is required only when the recognition path fails or returns an
  unusable result.

## Required Observability Fields

- `session_id`
- `recognition_path`
- `provider_id`
- `primary_transcript`
- `confidence_available`
- `confidence_score`
- `alternative_transcripts`
- `detected_language`
- `latency_ms`
- `error_code`

## Validation Expectations

- Unit coverage for confidence-present, confidence-missing, and
  alternative-transcript result shaping.
- Integration coverage for local-first then fallback recognition transitions.
- Smoke validation proving supported commands still complete through the first
  local path when fallback is unnecessary.
