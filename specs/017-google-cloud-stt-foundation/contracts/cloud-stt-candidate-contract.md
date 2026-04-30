# Cloud STT Candidate Contract

## Purpose

Define the structured output produced by the optional Google Cloud STT boundary
before successful command recognition is adapted into `CommandRecognitionResult`.

## Output Shape

```json
{
  "provider_source": "cloud_primary",
  "status": "recognized",
  "recognition_path": "local_first",
  "primary_transcript": "detect obstacle",
  "confidence_available": true,
  "confidence_score": 0.91,
  "alternative_transcripts": ["detect obstacle", "detect obstacles"],
  "selected_language": "en-US",
  "detected_language": "en-US",
  "latency_ms": 842,
  "failure_reason_code": null,
  "field_safe": true,
  "raw_user_content_persisted": false
}
```

## Failure Shape

```json
{
  "provider_source": "cloud_primary",
  "status": "failed",
  "recognition_path": "local_first",
  "primary_transcript": null,
  "confidence_available": false,
  "confidence_score": null,
  "alternative_transcripts": [],
  "selected_language": "ar-EG",
  "detected_language": null,
  "latency_ms": 3000,
  "failure_reason_code": "cloud_network_timeout",
  "field_safe": true,
  "raw_user_content_persisted": false
}
```

## Required Status Values

- `recognized`
- `empty_result`
- `unavailable`
- `failed`

## Required Failure Reason Codes

- `cloud_credentials_missing`
- `cloud_network_timeout`
- `cloud_auth_error`
- `cloud_quota_error`
- `cloud_service_unavailable`
- `cloud_empty_result`
- `cloud_unknown_failure`

## Rules

- `status=recognized` requires a non-empty `primary_transcript`.
- `status=empty_result` uses `failure_reason_code=cloud_empty_result`.
- `confidence_score`, when present, must be between `0.0` and `1.0`.
- `detected_language` is metadata only and must not mutate the selected
  profile language.
- `field_safe` must be `true` and `raw_user_content_persisted` must be `false`
  for default diagnostics and artifacts.
- Failure outcomes must not produce a usable transcript.
- Adaptation into `CommandRecognitionResult` must preserve
  `recognition_source=cloud_primary`, `selected_language`, and
  `detected_language` metadata.

## Validation Expectations

- Unit tests cover fake successful responses with one and many alternatives.
- Unit tests cover every required failure reason code.
- Integration tests prove recognized cloud candidates can populate existing
  command-recognition metadata without changing public listener methods.
- Privacy tests prove credentials and raw utterances are not persisted by
  default.
