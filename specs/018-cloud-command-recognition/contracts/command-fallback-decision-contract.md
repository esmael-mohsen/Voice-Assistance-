# Command Fallback Decision Contract

## Purpose

Define the field-safe decision shape used to explain whether command
recognition continues to normal policy, strict fallback, retry, confirmation,
safe refusal, or no usable transcript.

## Decision Shape

```json
{
  "decision_id": "cmd-fallback-session-123-1",
  "event_category": "command_recognition",
  "status_or_decision": "fallback",
  "trigger": "cloud_network_timeout",
  "recognition_source": "cloud_primary",
  "fallback_enabled": true,
  "fallback_attempted": true,
  "fallback_mode": "command_inventory",
  "reason_code": "cloud_network_timeout",
  "confidence_band": "missing_confidence",
  "selected_language": "en-US",
  "detected_language": null,
  "latency_ms": 3000,
  "field_safe": true,
  "raw_user_content_present": false
}
```

## Status Or Decision Values

- `execute`
- `fallback`
- `confirm`
- `retry`
- `defer`
- `refuse`
- `no_usable_transcript`

## Trigger Values

- `cloud_timeout`
- `cloud_empty_result`
- `cloud_unavailable`
- `cloud_low_confidence`
- `language_mismatch`
- `alternatives_conflict`
- `parser_rejected`
- `strict_grammar_no_match`
- `protected_command`
- `endpoint_quality`

## Rules

- Provider failure triggers must never resolve directly to `execute`.
- `strict_grammar_no_match` must never enable broad local dictation.
- If `fallback_enabled=false`, provider failure resolves to
  `no_usable_transcript` and existing recovery.
- If strict fallback matches, the matched candidate still passes through
  post-processing, parser, and confidence policy.
- Low confidence, language mismatch, parser rejection, and alternatives
  conflict use existing runtime policy to request fallback, confirmation,
  retry, or refusal.
- Protected commands cannot resolve to `execute` unless explicit affirmative
  confirmation has already been collected.
- Wake wording in command mode cannot increase confidence or bypass validation.
- Decision diagnostics must be field-safe and omit raw utterances by default.

## Validation Expectations

- Tests cover every provider-level trigger.
- Tests cover runtime-level triggers for low confidence, parser rejection,
  language mismatch, and alternatives conflict.
- Tests cover strict fallback disabled, strict fallback matched, and strict
  fallback no-match.
- Tests verify protected-command decisions require confirmation.
