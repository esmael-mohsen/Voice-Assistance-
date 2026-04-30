# Audio Capture Profile Contract

## Purpose

Define the machine-readable capture-policy payload used to configure speech
capture before transcription.

## Output Shape

```json
{
  "profile_id": "command.default",
  "usage_mode": "command",
  "sample_rate_hz": 16000,
  "mono_required": true,
  "high_pass_hz": 120,
  "target_loudness_dbfs": -20,
  "vad_enabled": true,
  "pre_roll_ms": 180,
  "post_roll_ms": 220,
  "trailing_silence_ms": 650,
  "max_utterance_ms": 8000,
  "allow_noise_suppression": false,
  "dictionary_bias_mode": "command_inventory",
  "closed_vocabulary_id": null
}
```

## Rules

- `usage_mode` must be one of `standby_wake`, `onboarding`, `command`, or
  `confirmation`.
- `sample_rate_hz` must be positive and supported by the active capture path.
- `pre_roll_ms`, `post_roll_ms`, and `trailing_silence_ms` must be
  non-negative.
- `dictionary_bias_mode=closed_choice` requires `closed_vocabulary_id`.
- `allow_noise_suppression` may be enabled only for qualification profiles that
  remain within Raspberry Pi 4 resource budgets.

## Required Observability Fields

- `profile_id`
- `usage_mode`
- `sample_rate_hz`
- `vad_enabled`
- `pre_roll_ms`
- `post_roll_ms`
- `trailing_silence_ms`
- `dictionary_bias_mode`
- `closed_vocabulary_id`

## Validation Expectations

- Unit coverage for profile normalization and validation.
- Integration coverage proving the correct profile is selected per listening
  mode.
- Qualification coverage showing which profile was active for a benchmark run.
