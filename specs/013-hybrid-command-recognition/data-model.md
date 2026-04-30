# Data Model: Hybrid Command Recognition and Post-Processing

## CommandRecognitionResult

- **Purpose**: Represents the structured outcome of one recognition attempt
  before parser matching and runtime safety decisions.
- **Fields**:
  - `session_id`
  - `recognition_path`: `local_first | fallback`
  - `provider_id`
  - `primary_transcript`
  - `confidence_score`
  - `confidence_available`
  - `alternative_transcripts`
  - `detected_language`
  - `latency_ms`
  - `error_code`
- **Validation Rules**:
  - `primary_transcript` must be present for any successful recognition result.
  - `confidence_available=false` requires `confidence_score=null`.
  - `recognition_path` must identify whether the result came from the first
    local path or the stronger fallback path.
  - `alternative_transcripts` may be empty but must preserve ranking order when
    populated.
  - `latency_ms` must be non-negative.
- **Relationships**:
  - input to `CommandPostProcessingOutcome`
  - evaluated by `ConfidenceDecisionOutcome`
  - summarized by `RecognitionTelemetrySample`

## CommandPostProcessingOutcome

- **Purpose**: Captures how a recognized transcript is normalized before parser
  matching.
- **Fields**:
  - `source_transcript`
  - `normalized_transcript`
  - `canonical_command_text`
  - `substitution_ids`
  - `language_hints`
  - `ambiguity_flags`
  - `post_processing_status`: `normalized | unchanged | rejected`
- **Validation Rules**:
  - `normalized_transcript` must always be populated when
    `post_processing_status` is `normalized` or `unchanged`.
  - `canonical_command_text` may differ from `normalized_transcript` only when
    a command-specific canonicalization rule applies.
  - `substitution_ids` must reference known substitution rules when present.
  - `ambiguity_flags` must explain why downstream confidence handling cannot
    safely execute immediately.
- **Relationships**:
  - derived from `CommandRecognitionResult`
  - input to parser matching and `ConfidenceDecisionOutcome`

## ConfidenceDecisionPolicy

- **Purpose**: Defines the thresholds and bounded decision rules that determine
  immediate execution, fallback, confirmation, retry, deferral, or refusal.
- **Fields**:
  - `high_confidence_threshold`
  - `medium_confidence_threshold`
  - `protected_command_threshold`
  - `allow_missing_confidence_for_unprotected`
  - `max_retry_cycles`
  - `fallback_enabled`
  - `offline_local_allowed`
- **Validation Rules**:
  - `high_confidence_threshold` must be greater than or equal to
    `medium_confidence_threshold`.
  - `protected_command_threshold` must be greater than or equal to
    `high_confidence_threshold`.
  - `max_retry_cycles` is fixed at `1` for this phase.
  - `offline_local_allowed=true` may apply only to commands the local path can
    handle safely without network fallback.
- **Relationships**:
  - consumed by `ConfidenceDecisionOutcome`
  - configured through runtime settings snapshots

## ConfidenceDecisionOutcome

- **Purpose**: Represents the runtime’s action after combining recognition,
  post-processing, parser, and safety information.
- **Fields**:
  - `intent_id`
  - `decision_band`: `high | medium | low | missing_confidence`
  - `decision_action`: `execute | fallback | confirm | retry | defer | refuse`
  - `protected_command`
  - `fallback_attempted`
  - `confirmation_required`
  - `retry_count`
  - `spoken_guidance_surface`
  - `reason_code`
- **Validation Rules**:
  - `decision_action=execute` requires either `decision_band=high` or
    `decision_band=missing_confidence` with a single unambiguous
    non-protected interpretation.
  - Protected commands must never reach `execute` without explicit affirmative
    confirmation when below the protected threshold.
  - `retry_count` must not exceed the policy’s `max_retry_cycles`.
  - `fallback_attempted=false` requires `decision_action` to be explainable by
    local-only evidence.
- **Relationships**:
  - aggregates parser and runtime safety information
  - summarized by `RecognitionTelemetrySample`

## RecognitionTelemetrySample

- **Purpose**: Records reviewable metadata about one command-recognition
  interaction without storing raw utterances by default.
- **Fields**:
  - `session_id`
  - `event_id`
  - `recognition_path`
  - `confidence_band`
  - `fallback_used`
  - `decision_outcome`
  - `protected_command`
  - `latency_ms`
  - `field_safe`
  - `raw_utterance_present`
- **Validation Rules**:
  - `field_safe=true` requires `raw_utterance_present=false`.
  - `confidence_band` must match the band used in `ConfidenceDecisionOutcome`.
  - `fallback_used=true` requires `recognition_path` to show that fallback was
    actually invoked.
  - `latency_ms` must capture the end-to-end recognition decision latency for
    the interaction.
- **Relationships**:
  - derived from `CommandRecognitionResult` and `ConfidenceDecisionOutcome`
  - emitted by the runtime for observability and release review

## State Transitions

- `local_listen_started -> local_result_ready -> post_processed`
- `post_processed -> execute_ready` when the command is high confidence or
  unambiguous missing-confidence and non-protected
- `post_processed -> fallback_requested -> fallback_result_ready -> post_processed`
- `post_processed -> confirmation_required -> execute_ready` after explicit
  affirmative confirmation
- `post_processed -> retry_prompted -> local_listen_started` for one bounded
  additional retry
- `post_processed -> safe_refusal` when the command remains low confidence,
  ambiguous, offline-unsupported, or unconfirmed while protected
