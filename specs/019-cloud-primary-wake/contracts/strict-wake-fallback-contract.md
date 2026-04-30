# Strict Wake Fallback Contract

## Purpose

Define the strict local Vosk wake grammar behavior used after cloud-primary
wake fails or returns a non-canonical transcript.

## Input Shape

```json
{
  "fallback_mode": "wake_grammar",
  "usage_mode": "standby_wake",
  "language_candidates": ["en-US", "ar-EG"],
  "grammar_phrases": ["hi egb", "hey egb", "marhaba", "مرحبا"],
  "allow_freeform": false
}
```

## Matched Output Shape

```json
{
  "recognition_source": "wake_strict_vosk_fallback",
  "fallback_mode": "wake_grammar",
  "status": "matched",
  "primary_transcript": "marhaba",
  "matched_phrase": "marhaba",
  "canonical_wake_alias": "مرحبا",
  "confidence_available": true,
  "confidence_score": 0.81,
  "detected_language": "ar-EG",
  "failure_reason_code": null,
  "latency_ms": 290
}
```

## No-Match Shape

```json
{
  "recognition_source": "wake_strict_vosk_fallback",
  "fallback_mode": "wake_grammar",
  "status": "no_match",
  "primary_transcript": null,
  "matched_phrase": null,
  "canonical_wake_alias": null,
  "confidence_available": false,
  "confidence_score": null,
  "detected_language": "en-US",
  "failure_reason_code": "strict_grammar_no_match",
  "latency_ms": 260
}
```

## Rules

- `allow_freeform` must always be `false`.
- `status=matched` requires `matched_phrase` to exist in `grammar_phrases`.
- `status=no_match` must not expose a usable transcript.
- Command-only or unrelated speech must resolve to `no_match`.
- PocketSphinx is excluded from the default strict wake fallback path.
- Adapted matched results must expose
  `recognition_source=wake_strict_vosk_fallback`.

## Validation Expectations

- Unit tests cover valid wake matches, non-wake phrases, similar-sounding
  misses, unavailable Vosk, and grammar no-match outcomes.
- Integration tests prove strict local wake fallback does not accept arbitrary
  free-form speech.
- Privacy and diagnostics tests prove fallback results remain field-safe.
