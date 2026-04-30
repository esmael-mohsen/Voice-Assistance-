# Wake Recognition Result Contract

## Purpose

Define the speech-based wake recognition payload consumed by the wake service
and `AssistantRuntime` before the runtime decides wake accepted, rejected, or
missed.

## Success Shape

```json
{
  "attempt_id": "wake-123",
  "recognition_path": "standby_wake",
  "selected_wake_mode": "stt_based_wake",
  "recognition_source": "cloud_primary",
  "status": "recognized",
  "primary_transcript": "hi egb open navigation",
  "matched_canonical_alias": "hi egb",
  "canonical_gate_passed": true,
  "command_suffix_ignored": true,
  "confidence_available": true,
  "confidence_score": 0.93,
  "selected_language": "en-US",
  "detected_language": "en-US",
  "language_candidates": ["en-US", "ar-EG"],
  "failure_reason_code": null,
  "latency_ms": 1240,
  "field_safe": true,
  "raw_user_content_present": false
}
```

## No Usable Transcript Shape

```json
{
  "attempt_id": "wake-123",
  "recognition_path": "standby_wake",
  "selected_wake_mode": "stt_based_wake",
  "recognition_source": "wake_strict_vosk_fallback",
  "status": "no_match",
  "primary_transcript": "",
  "matched_canonical_alias": null,
  "canonical_gate_passed": false,
  "command_suffix_ignored": false,
  "confidence_available": false,
  "confidence_score": null,
  "selected_language": "ar-EG",
  "detected_language": null,
  "language_candidates": ["ar-EG", "en-US"],
  "failure_reason_code": "strict_grammar_no_match",
  "latency_ms": 310,
  "field_safe": true,
  "raw_user_content_present": false
}
```

## Recognition Source Values

- `cloud_primary`
- `wake_strict_vosk_fallback`
- `cloud_unavailable`
- `keyword_low_power`
- `hardware_trigger`

## Rules

- A successful STT recognition result does not by itself accept wake; the
  canonical wake gate must still pass.
- `canonical_gate_passed=true` requires `matched_canonical_alias` to be
  present.
- `command_suffix_ignored=true` means the wake was accepted but any trailing
  command text from the same utterance must not be executed or queued.
- No-usable-transcript results must include a stable `failure_reason_code`.
- `wake_strict_vosk_fallback` is reserved for strict local wake grammar
  matches or no-match outcomes.
- Default diagnostics must keep `field_safe=true` and
  `raw_user_content_present=false`.

## Validation Expectations

- Unit tests cover canonical wake success, non-canonical rejection, wake-plus-
  command wake-only handling, and no-match fallback outcomes.
- Integration tests prove standby runtime consumers accept the extended wake
  metadata without changing the existing standby authority.
- Privacy tests prove no raw utterances or credentials are persisted by
  default.
