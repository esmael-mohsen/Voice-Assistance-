# Command Recognition Result Contract

## Purpose

Define the command-mode recognition shape consumed by `AssistantRuntime`,
post-processing, parser, confidence policy, diagnostics, dispatcher, and
resolver after Phase 18 command ordering changes.

## Success Shape

```json
{
  "session_id": "session-123",
  "recognition_path": "local_first",
  "provider_id": "legacy",
  "recognition_source": "cloud_primary",
  "primary_transcript": "detect obstacle",
  "alternative_transcripts": ["detect obstacle", "detect obstacles"],
  "confidence_available": true,
  "confidence_score": 0.91,
  "selected_language": "en-US",
  "detected_language": "en-US",
  "language_candidates": ["en-US", "ar-EG"],
  "endpoint_quality_hints": [],
  "failure_reason_code": null,
  "latency_ms": 842,
  "field_safe": true,
  "raw_user_content_present": false
}
```

## No Usable Transcript Shape

```json
{
  "session_id": "session-123",
  "recognition_path": "local_first",
  "provider_id": "legacy",
  "recognition_source": "strict_vosk_fallback",
  "primary_transcript": "",
  "alternative_transcripts": [],
  "confidence_available": false,
  "confidence_score": null,
  "selected_language": "ar-EG",
  "detected_language": null,
  "language_candidates": ["ar-EG", "en-US"],
  "endpoint_quality_hints": [],
  "failure_reason_code": "strict_grammar_no_match",
  "error_code": "strict_grammar_no_match",
  "latency_ms": 310,
  "field_safe": true,
  "raw_user_content_present": false
}
```

## Recognition Source Values

- `cloud_primary`
- `strict_vosk_fallback`
- `rescue_strict_vosk`
- `cloud_unavailable`
- `local_vosk`
- `sphinx_compat`
- `legacy_local`

## Recognition Path Values

- `local_first`
- `rescue`
- `fallback`

## Rules

- Successful results require a non-empty `primary_transcript`.
- No-usable-transcript results must include `error_code` and a stable
  `failure_reason_code`.
- `confidence_score` must be `null` unless `confidence_available=true`.
- `confidence_score`, when present, must be between `0.0` and `1.0`.
- `selected_language` is the active runtime/profile language for the attempt.
- `detected_language` is metadata only and must not mutate profile language.
- `alternative_transcripts` must preserve provider ordering when available.
- `field_safe` must be `true` and `raw_user_content_present` must be `false`
  for default diagnostics and artifacts.
- `sphinx_compat` is allowed only when explicit compatibility is enabled.

## Validation Expectations

- Unit tests cover cloud success with one and many alternatives.
- Unit tests cover no-usable-transcript results for cloud failure with strict
  fallback disabled and strict fallback no-match.
- Integration tests prove existing runtime consumers accept the extended
  metadata without changing public listener method names.
- Privacy tests prove no raw utterances or credential material are persisted by
  default.
