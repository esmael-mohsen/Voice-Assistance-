# Command Safety Evaluation Contract

## Purpose

Define how cloud-primary and strict fallback command candidates interact with
the existing parser, confidence policy, protected-command confirmation,
dispatcher, and resolver flow.

## Input Shape

```json
{
  "primary_transcript": "stop system",
  "alternative_transcripts": ["stop system", "start system"],
  "recognition_source": "cloud_primary",
  "confidence_available": true,
  "confidence_score": 0.94,
  "selected_language": "en-US",
  "detected_language": "en-US",
  "endpoint_quality_hints": [],
  "recognition_path": "local_first"
}
```

## Evaluation Shape

```json
{
  "parsed_intent_id": "system.stop",
  "risk_level": "protected",
  "requires_confirmation": true,
  "confidence_band": "high",
  "alternatives_conflict": false,
  "language_mismatch": false,
  "endpoint_quality_penalty_applied": false,
  "decision_action": "confirm",
  "confirmation_required": true,
  "fallback_allowed": true
}
```

## Decision Action Values

- `execute`
- `fallback`
- `confirm`
- `retry`
- `defer`
- `refuse`

## Rules

- All candidates must pass command post-processing and parser validation.
- Existing command confidence thresholds remain authoritative.
- Cloud confidence is considered only as policy input.
- Protected commands require explicit affirmative confirmation regardless of
  cloud confidence.
- Medium-risk or ambiguous commands confirm or retry when confidence is
  borderline or alternatives conflict.
- Low-risk commands may execute directly only when confidence is high and
  parser acceptance is clean.
- Language mismatch, endpoint clipping, no command-like shape, and conflicting
  alternatives must penalize trust or route to recovery.
- Wake wording in command mode may be ignored or stripped, but it cannot count
  as confirmation.
- Dispatcher and resolver receive commands only after this evaluation permits
  execution.

## Validation Expectations

- Tests cover low-risk high-confidence execution.
- Tests cover medium-risk borderline confirmation/retry.
- Tests cover protected high-confidence confirmation.
- Tests cover conflicting alternatives.
- Tests cover parser rejection and safe recovery.
- Tests cover wake-plus-protected-command confirmation.
