# Data Model: Audio Front-End, Hybrid STT, and Command Canonicalization

## AudioCaptureProfile

- **Purpose**: Defines how a listening mode captures and prepares speech before
  transcription.
- **Fields**:
  - `profile_id`
  - `usage_mode`: `standby_wake | onboarding | command | confirmation`
  - `sample_rate_hz`
  - `mono_required`
  - `high_pass_hz`
  - `target_loudness_dbfs`
  - `vad_enabled`
  - `pre_roll_ms`
  - `post_roll_ms`
  - `trailing_silence_ms`
  - `max_utterance_ms`
  - `allow_noise_suppression`
  - `dictionary_bias_mode`: `none | command_inventory | closed_choice`
  - `closed_vocabulary_id`
- **Validation Rules**:
  - `profile_id` must be unique per deployment profile.
  - `usage_mode` must map to exactly one runtime listening context.
  - `sample_rate_hz` must be supported by the capture pipeline and stay
    positive.
  - `pre_roll_ms`, `post_roll_ms`, and `trailing_silence_ms` must be
    non-negative.
  - `closed_vocabulary_id` is required when `dictionary_bias_mode=closed_choice`.
- **Relationships**:
  - configures `AudioCaptureAttempt`
  - referenced by `SpeechBenchmarkFixture`
  - selected through runtime settings snapshots

## AudioCaptureAttempt

- **Purpose**: Represents one command-capture attempt, including preprocessing,
  endpointing, and bounded relisten state.
- **Fields**:
  - `capture_attempt_id`
  - `session_id`
  - `profile_id`
  - `attempt_index`
  - `started_at_ms`
  - `ended_at_ms`
  - `raw_duration_ms`
  - `processed_duration_ms`
  - `speech_started_at_ms`
  - `speech_ended_at_ms`
  - `utterance_duration_ms`
  - `clipping_start_suspected`
  - `clipping_end_suspected`
  - `endpoint_quality_hints`
  - `relisten_triggered`
  - `recovery_prompt_surface`
- **Validation Rules**:
  - `attempt_index` must start at `0` and never exceed `1` for the bounded
    relisten path in this phase.
  - `ended_at_ms` must be greater than or equal to `started_at_ms`.
  - `utterance_duration_ms` must be non-negative and must not exceed
    `max_utterance_ms` from the referenced profile.
  - `relisten_triggered=true` requires at least one clipping or endpoint
    quality hint.
- **Relationships**:
  - derived from `AudioCaptureProfile`
  - summarized inside `HybridRecognitionResult`
  - used by runtime recovery decisions

## HybridRecognitionResult

- **Purpose**: Represents the structured recognition outcome after local-first
  decoding and any bounded rescue behavior.
- **Fields**:
  - `session_id`
  - `capture_attempt_id`
  - `recognition_path`: `local_first | rescue`
  - `provider_id`
  - `profile_id`
  - `primary_transcript`
  - `alternative_transcripts`
  - `confidence_score`
  - `confidence_available`
  - `detected_language`
  - `language_candidates`
  - `latency_ms`
  - `dictionary_bias_applied`
  - `closed_vocabulary_id`
  - `endpoint_quality_hints`
  - `error_code`
- **Validation Rules**:
  - `primary_transcript` is required for successful recognition results.
  - `recognition_path` must identify whether the result came from the local
    decode or the rescue step.
  - `confidence_available=false` requires `confidence_score=null`.
  - `dictionary_bias_applied=true` requires a profile or mode that supports
    dictionary filtering.
  - `latency_ms` must be non-negative.
- **Relationships**:
  - consumes `AudioCaptureAttempt`
  - input to `CanonicalCommandOutcome`
  - summarized by qualification telemetry and benchmark evidence

## CanonicalCommandOutcome

- **Purpose**: Captures transcript normalization, alias mapping, confusion-pair
  handling, and parser-ready canonical command text.
- **Fields**:
  - `source_transcript`
  - `normalized_transcript`
  - `canonical_command_text`
  - `substitution_ids`
  - `language_hints`
  - `dictionary_mode`
  - `closed_vocabulary_id`
  - `confusion_pair_id`
  - `ambiguity_flags`
  - `canonicalization_status`: `unchanged | normalized | constrained_retry | rejected`
- **Validation Rules**:
  - `canonical_command_text` must be populated for `unchanged` and
    `normalized` outcomes.
  - `canonicalization_status=constrained_retry` requires a closed vocabulary or
    constrained mode context.
  - `confusion_pair_id` must reference a known pair when present.
  - `ambiguity_flags` must explain why the runtime cannot auto-execute or map
    the result safely.
- **Relationships**:
  - derived from `HybridRecognitionResult`
  - input to parser matching, confirmation flow, and safe-refusal logic

## SpeechQualificationProfile

- **Purpose**: Describes the supported deployment profile being qualified for
  Raspberry Pi 4-class hardware.
- **Fields**:
  - `qualification_profile_id`
  - `profile_label`: `default | simplified`
  - `enable_noise_suppression`
  - `enable_rescue_recognition`
  - `enable_dictionary_bias`
  - `enable_capture_relisten`
  - `qualification_status`: `candidate | qualified | demoted`
  - `demotion_reason`
  - `evidence_bundle_id`
- **Validation Rules**:
  - `qualification_status=demoted` requires `demotion_reason`.
  - `profile_label` must be unique within a release candidate.
  - `default` profiles may not remain active if they breach the declared Pi 4
    budget during qualification.
- **Relationships**:
  - selects which `AudioCaptureProfile` variants are active
  - referenced by `SpeechBenchmarkFixture`
  - summarized in release or qualification evidence

## SpeechBenchmarkFixture

- **Purpose**: Represents a curated offline benchmark case used to validate
  capture completeness, recognition quality, canonicalization, and latency.
- **Fields**:
  - `fixture_id`
  - `scenario_type`: `noisy_room | clipped_start | clipped_end | bilingual | closed_choice | disagreement`
  - `profile_id`
  - `qualification_profile_id`
  - `source_language`
  - `expected_canonical_text`
  - `expected_closed_choice_option`
  - `expected_decision`
  - `audio_asset_ref`
  - `field_safe`
  - `notes`
- **Validation Rules**:
  - `audio_asset_ref` must point to a curated offline sample, not a live-user
    runtime artifact.
  - `field_safe` must remain `true` for default benchmark evidence metadata.
  - Each fixture must define either `expected_canonical_text` or
    `expected_closed_choice_option`.
- **Relationships**:
  - executed against `AudioCaptureProfile` and `SpeechQualificationProfile`
  - produces evidence for success-criteria validation

## State Transitions

- `capture_profile_selected -> capture_started -> audio_preprocessed -> endpoint_scored`
- `endpoint_scored -> relisten_requested -> capture_started` when clipping is
  suspected and no relisten has been used yet
- `endpoint_scored -> local_decode_ready -> local_result_ready`
- `local_result_ready -> rescue_requested -> rescue_result_ready` when the
  result is weak, clipped, contradictory, or outside a constrained answer set
- `local_result_ready -> canonicalized` when the local-first result is usable
- `rescue_result_ready -> canonicalized`
- `canonicalized -> parser_ready` when the transcript maps to a safe canonical
  command or valid closed-choice answer
- `canonicalized -> constrained_retry_prompted` when a constrained mode needs
  one short retry
- `canonicalized -> confirmation_required` when local and rescue paths disagree
  on a non-protected command or confidence remains too weak for direct action
- `canonicalized -> safe_refusal` when the result remains ambiguous, risky, or
  unsupported after the bounded recovery path
- `qualification_candidate -> qualified` when the configured profile meets Pi 4
  latency and quality budgets
- `qualification_candidate -> demoted` when an optional enhancement breaches
  the qualification budget and must be disabled in the default profile
