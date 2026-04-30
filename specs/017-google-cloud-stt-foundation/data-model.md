# Data Model: Google Cloud STT Foundation and Strict Fallback Contracts

## CloudRecognitionCandidate

- **Purpose**: Represents one candidate returned by the cloud recognition
  boundary before it is adapted into runtime command recognition metadata.
- **Fields**:
  - `candidate_id`
  - `provider_source`: `cloud_primary`
  - `status`: `recognized | empty_result | unavailable | failed`
  - `transcript`
  - `normalized_transcript`
  - `confidence_score`
  - `confidence_available`
  - `alternative_transcripts`
  - `selected_language`
  - `detected_language`
  - `latency_ms`
  - `failure_reason_code`
- **Validation Rules**:
  - `status=recognized` requires a non-empty `normalized_transcript`.
  - `confidence_score`, when present, must be between `0.0` and `1.0`.
  - `failure_reason_code` must be empty for successful candidates and present
    for failed or unavailable outcomes.
  - `detected_language` is metadata only and must not mutate the selected
    profile language.
- **Relationships**:
  - emitted by `GoogleCloudRecognitionAttempt`
  - may be adapted into `CommandRecognitionResult`
  - may be summarized by `RecognitionDiagnosticEvent`

## GoogleCloudRecognitionAttempt

- **Purpose**: Captures one bounded cloud recognition call and its retry
  behavior.
- **Fields**:
  - `attempt_id`
  - `session_id`
  - `usage_mode`
  - `audio_encoding`
  - `sample_rate_hz`
  - `selected_language`
  - `phrase_hint_set_id`
  - `timeout_s`
  - `retry_count`
  - `max_alternatives`
  - `credential_state`
  - `started_at_ms`
  - `ended_at_ms`
- **Validation Rules**:
  - `timeout_s` defaults to `3.0` and must be positive.
  - `retry_count` must be `0` or `1` for Phase 17.
  - `credential_state=missing` must produce no client request.
  - `usage_mode` must align with an approved phrase-hint mode.
- **Relationships**:
  - consumes `RecognitionConfiguration`
  - consumes one `PhraseHintSet`
  - produces zero or more `CloudRecognitionCandidate` records

## ProviderAvailabilityState

- **Purpose**: Captures whether the cloud STT boundary is usable for the
  current runtime session without exposing credential material.
- **Fields**:
  - `provider_source`: `cloud_primary | strict_vosk_fallback | sphinx_compat`
  - `availability`: `ready | degraded | unavailable`
  - `credential_state`: `available | missing | invalid | not_required`
  - `client_import_state`: `available | missing`
  - `network_required`
  - `startup_safe`
  - `reason_code`
  - `checked_at_ms`
- **Validation Rules**:
  - `startup_safe` must remain `true` when cloud credentials or the optional
    cloud client package are missing.
  - `credential_state` must not contain credential paths, JSON content, or
    secret values.
  - `availability=unavailable` requires a field-safe `reason_code`.
  - `sphinx_compat` availability must not affect default production wake or
    command decisions unless compatibility is explicitly enabled.
- **Relationships**:
  - reported by provider metadata and startup diagnostics
  - consumed by `RecognitionConfiguration`
  - summarized by `RecognitionDiagnosticEvent`

## FailureReasonCode

- **Purpose**: Stable classification for cloud recognition failures.
- **Allowed Values**:
  - `cloud_credentials_missing`
  - `cloud_network_timeout`
  - `cloud_auth_error`
  - `cloud_quota_error`
  - `cloud_service_unavailable`
  - `cloud_empty_result`
  - `cloud_unknown_failure`
- **Validation Rules**:
  - Every failed or unavailable cloud result must map to exactly one value.
  - `cloud_empty_result` is used only when the provider call succeeds but no
    usable transcript is present.
  - Timeout, auth, quota, and service failures must not be collapsed into
    `cloud_unknown_failure` when the exception category is known.
- **Relationships**:
  - referenced by `CloudRecognitionCandidate`
  - referenced by `RecognitionDiagnosticEvent`

## PhraseHintSet

- **Purpose**: Deterministic phrase inventory for one recognition mode.
- **Fields**:
  - `phrase_hint_set_id`
  - `mode`: `wake | command | confirmation | onboarding`
  - `language_scope`: `english | arabic | bilingual`
  - `source_catalogs`
  - `phrases`
  - `variant_types`
  - `generated_at_build_id`
  - `raw_user_content_present`
- **Validation Rules**:
  - `phrases` must be deterministic for identical source catalogs.
  - `phrases` must not include empty strings or duplicates after
    normalization.
  - `variant_types` must include expected categories for the mode, such as
    `canonical`, `arabic`, `english`, `bilingual`, `phonetic`, or
    `stt_mistake`.
  - `raw_user_content_present` must be `false` by default.
- **Relationships**:
  - built from `core.parser.COMMAND_CATALOG`, closed-vocabulary contexts, wake
    aliases, assistive phrases, and safety-critical commands
  - referenced by `GoogleCloudRecognitionAttempt`
  - referenced by `StrictVoskFallbackContract`

## StrictVoskFallbackContract

- **Purpose**: Defines the allowed local fallback vocabulary and no-match
  behavior for one interaction mode.
- **Fields**:
  - `fallback_contract_id`
  - `mode`: `wake_grammar | command_inventory | closed_choice`
  - `usage_mode`
  - `language_candidates`
  - `grammar_phrases`
  - `closed_vocabulary_id`
  - `allow_freeform`
  - `no_match_behavior`
  - `sphinx_fallback_allowed`
- **Validation Rules**:
  - `allow_freeform` must be `false` for all Phase 17 production modes.
  - `no_match_behavior` must be `return_no_usable_transcript`.
  - `closed_choice` mode requires `closed_vocabulary_id`.
  - `sphinx_fallback_allowed` must be `false` unless compatibility is
    explicitly enabled for debugging.
- **Relationships**:
  - consumes `PhraseHintSet` or closed-vocabulary choices
  - produces `StrictVoskFallbackOutcome`

## StrictVoskFallbackOutcome

- **Purpose**: Represents the result of a strict local fallback attempt.
- **Fields**:
  - `fallback_contract_id`
  - `status`: `matched | no_match | unavailable | failed`
  - `transcript`
  - `matched_phrase`
  - `confidence_score`
  - `language`
  - `failure_reason`
  - `latency_ms`
- **Validation Rules**:
  - `status=matched` requires `matched_phrase` to exist in the active grammar.
  - `status=no_match` must not expose a usable transcript.
  - `status=unavailable` must not trigger PocketSphinx unless compatibility is
    explicitly enabled.
- **Relationships**:
  - may be adapted into `CommandRecognitionResult`
  - summarized by `RecognitionDiagnosticEvent`

## RecognitionConfiguration

- **Purpose**: Captures the effective STT rollout and compatibility controls
  for a runtime session.
- **Fields**:
  - `cloud_primary_enabled`
  - `strict_vosk_fallback_enabled`
  - `sphinx_compat_enabled`
  - `cloud_timeout_s`
  - `cloud_max_alternatives`
  - `configured_from_environment`
  - `selected_profile_language`
- **Validation Rules**:
  - Defaults are cloud primary off, strict Vosk fallback off, and PocketSphinx
    compatibility off.
  - `cloud_timeout_s` defaults to `3.0` and must be positive.
  - `cloud_max_alternatives` must be at least `1`.
  - Effective configuration must be loggable without secrets.
- **Relationships**:
  - consumed by cloud attempts, strict fallback contracts, and diagnostics

## LanguageMetadata

- **Purpose**: Separates selected profile language from detected recognition
  language.
- **Fields**:
  - `selected_language`
  - `detected_language`
  - `language_candidates`
  - `source`
  - `profile_mutation_allowed`
- **Validation Rules**:
  - `profile_mutation_allowed` is `false` for cloud recognition metadata.
  - Detected language may be absent.
  - Detected language must be included in candidate metadata when available.
- **Relationships**:
  - attached to `CloudRecognitionCandidate`
  - attached to `CommandRecognitionResult`

## RecognitionDiagnosticEvent

- **Purpose**: Field-safe observability payload for provider selection,
  recognition source, fallback decisions, and failure reasons.
- **Fields**:
  - `event_category`
  - `session_or_run_id`
  - `provider_source`
  - `usage_mode`
  - `status_or_decision`
  - `reason_code`
  - `latency_ms`
  - `fallback_mode`
  - `field_safe`
  - `raw_user_content_present`
  - `credential_material_present`
- **Validation Rules**:
  - `field_safe` must be `true` for default logs and release artifacts.
  - `raw_user_content_present` must be `false` by default.
  - `credential_material_present` must be `false`.
  - `reason_code` must use `FailureReasonCode` when the event describes a
    cloud failure.
- **Relationships**:
  - summarizes cloud attempts, strict Vosk outcomes, fallback decisions, and
    PocketSphinx compatibility decisions.

## State Transitions

- `cloud_primary_disabled -> existing_local_compatible_path` when the rollout
  flag is off.
- `cloud_primary_enabled -> credential_check -> cloud_unavailable` when
  credentials are missing.
- `credential_check -> provider_availability_unavailable` when the cloud
  client package or credentials are missing while startup remains safe.
- `credential_check -> cloud_attempt -> cloud_candidate_selected` when a
  usable transcript is returned.
- `cloud_attempt -> transient_retry -> cloud_candidate_selected` when the first
  transient failure recovers within the listen window.
- `cloud_attempt -> cloud_failure_classified -> strict_vosk_fallback` when
  cloud fails and strict Vosk fallback is enabled.
- `cloud_failure_classified -> no_usable_transcript -> existing_recovery` when
  strict Vosk fallback is disabled.
- `strict_vosk_fallback -> matched -> command_result_candidate` when the
  transcript matches the active grammar.
- `strict_vosk_fallback -> no_match -> existing_recovery` when the transcript
  is outside the active grammar.
- `pocketsphinx_available -> ignored_by_default` unless
  `EGB_STT_ENABLE_SPHINX_COMPAT=1`.
