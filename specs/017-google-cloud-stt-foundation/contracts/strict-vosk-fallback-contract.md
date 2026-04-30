# Strict Vosk Fallback Contract

## Purpose

Define how Vosk fallback behaves when used as a strict local fallback after
cloud recognition is disabled or unavailable.

## Input Shape

```json
{
  "fallback_mode": "command_inventory",
  "usage_mode": "command",
  "language_candidates": ["en-US", "ar-EG"],
  "closed_vocabulary_id": null,
  "grammar_phrases": ["detect obstacle", "recognize face", "stop system"],
  "allow_freeform": false,
  "sphinx_fallback_allowed": false
}
```

## Output Shape

```json
{
  "fallback_mode": "command_inventory",
  "status": "matched",
  "primary_transcript": "detect obstacle",
  "matched_phrase": "detect obstacle",
  "confidence_available": true,
  "confidence_score": 0.74,
  "detected_language": "en-US",
  "failure_reason": null,
  "latency_ms": 310
}
```

## No-Match Shape

```json
{
  "fallback_mode": "closed_choice",
  "status": "no_match",
  "primary_transcript": null,
  "matched_phrase": null,
  "confidence_available": false,
  "confidence_score": null,
  "detected_language": "ar-EG",
  "failure_reason": "strict_grammar_no_match",
  "latency_ms": 260
}
```

## Fallback Modes

- `wake_grammar`
- `command_inventory`
- `closed_choice`

## Rules

- `allow_freeform` must be `false` in all Phase 17 production modes.
- `status=matched` requires `matched_phrase` to exist in `grammar_phrases`.
- `status=no_match` must not expose a usable transcript.
- `closed_choice` requires `closed_vocabulary_id`.
- PocketSphinx must not be called unless `sphinx_fallback_allowed=true` and
  `EGB_STT_ENABLE_SPHINX_COMPAT=1`.
- When cloud fails and strict Vosk fallback is disabled, the runtime returns no
  usable transcript and uses existing recovery behavior.
- Adapted success results should expose
  `recognition_source=strict_vosk_fallback` in `CommandRecognitionResult`.

## Validation Expectations

- Unit tests cover valid matches, near misses, unrelated speech, empty grammar,
  unavailable Vosk, and no-match outcomes.
- Integration tests prove command mode does not accept arbitrary free-form Vosk
  text.
- Compatibility tests prove PocketSphinx is excluded by default.
