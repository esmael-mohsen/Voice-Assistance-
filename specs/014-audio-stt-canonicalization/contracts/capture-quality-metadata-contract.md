# Capture Quality Metadata Contract

## Purpose

Define the structured capture metadata emitted for each command-capture
attempt before or alongside transcription.

## Output Shape

```json
{
  "capture_attempt_id": "cap-42",
  "session_id": "session-42",
  "profile_id": "command.default",
  "attempt_index": 0,
  "speech_started_at_ms": 140,
  "speech_ended_at_ms": 1820,
  "utterance_duration_ms": 1680,
  "clipping_start_suspected": false,
  "clipping_end_suspected": true,
  "endpoint_quality_hints": [
    "low_trailing_silence"
  ],
  "relisten_triggered": false,
  "recovery_prompt_surface": null
}
```

## Rules

- `attempt_index` must start at `0` and must not exceed `1` in this phase.
- `utterance_duration_ms` must be non-negative.
- `relisten_triggered=true` requires either a clipping flag or an endpoint
  quality hint.
- `recovery_prompt_surface` is required only when the bounded relisten path is
  used.

## Required Observability Fields

- `capture_attempt_id`
- `session_id`
- `profile_id`
- `attempt_index`
- `speech_started_at_ms`
- `speech_ended_at_ms`
- `utterance_duration_ms`
- `clipping_start_suspected`
- `clipping_end_suspected`
- `endpoint_quality_hints`
- `relisten_triggered`

## Validation Expectations

- Unit coverage for clipping-flag shaping and bounded relisten eligibility.
- Integration coverage for endpoint-aware capture and recovery prompts.
- Smoke validation proving capture metadata is available during normal command
  handling.
