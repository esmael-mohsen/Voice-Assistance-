# Interrupt Signal Contract

## Purpose

Define the machine-readable interrupt-detection payload used by runtime input
handling before dispatch or playback continuation.

## Input Shape

```json
{
  "raw_utterance": "stop now",
  "normalized_utterance": "stop now",
  "active_runtime_state": "speaking",
  "active_language": "ar-EG",
  "current_provider_id": "legacy"
}
```

## Output Shape

```json
{
  "accepted": true,
  "signal_type": "stop",
  "matched_vocabulary_ids": ["interrupt-stop-en"],
  "global_safety_phrase": true,
  "active_runtime_state": "speaking",
  "runtime_load_profile": "moderate"
}
```

## Rules

- `signal_type` must be one of: `stop`, `cancel`, `emergency`, `none`.
- `accepted=true` requires a non-empty `matched_vocabulary_ids` set and a
  non-`none` `signal_type`.
- Detection must remain valid even when `active_language` differs from the
  language family of the accepted safety phrase.
- Unrelated speech must remain non-accepting and must not interrupt playback or
  dispatch.

## Required Observability Fields

- `accepted`
- `signal_type`
- `normalized_utterance`
- `matched_vocabulary_ids`
- `active_runtime_state`
- `active_language`
- `runtime_load_profile`

## Validation Expectations

- Unit coverage for Arabic and English stop/cancel variants.
- Regression coverage for unrelated or noisy input that must not interrupt.
- Integration coverage for accepted interrupt detection during active runtime
  states.
