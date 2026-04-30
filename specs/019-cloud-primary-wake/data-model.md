# Data Model: Cloud-Primary Wake Recognition and Standby Fallback Reliability

## ApprovedWakeAliasCatalog

**Purpose**: Defines the authoritative canonical wake aliases and curated safe
variants used by cloud hints, strict local wake grammar, and final wake
acceptance.

**Fields**:
- `catalog_id`: Stable identifier such as `wake.default`.
- `canonical_aliases`: Ordered canonical forms, including `hi egb` and
  `مرحبا`.
- `approved_variants`: Curated English, Arabic, bilingual, phonetic, and
  common STT-safe variants.
- `language_scopes`: `english | arabic | bilingual`.
- `variant_types`: `canonical | english | arabic | bilingual | phonetic |
  stt_mistake`.
- `cloud_hint_cap`: Default `24`.
- `strict_grammar_cap`: Default `32`.
- `raw_user_content_present`: `false` by default.

**Validation Rules**:
- Canonical aliases must be non-empty after normalization.
- Variants must be curated and must not be learned from raw user transcripts by
  default.
- Duplicate phrases are removed after normalization.
- `cloud_hint_cap` must be less than or equal to `strict_grammar_cap`.

**Relationships**:
- Produces `WakePhraseHintSet`.
- Produces strict fallback `grammar_phrases`.
- Supplies the final canonical wake gate in `core/wake_word.py`.

## WakePhraseHintSet

**Purpose**: Represents the deterministic wake-specific phrase inventory used
to bias cloud wake recognition and build strict local wake grammar payloads.

**Fields**:
- `phrase_hint_set_id`
- `mode`: `wake`
- `language_scope`
- `source_catalogs`
- `variant_types`
- `max_cloud_phrases`
- `max_strict_grammar_phrases`
- `phrases`
- `raw_user_content_present`

**Validation Rules**:
- Phrase order must be deterministic for identical inputs.
- Canonical aliases must always remain in the hint set.
- Empty phrases and duplicates are removed after normalization.
- The cloud wake hint inventory must stay within the configured cap.

**Relationships**:
- Derived from `ApprovedWakeAliasCatalog`.
- Consumed by `WakeRecognitionAttempt`.
- Consumed by `StrictWakeFallbackOutcome`.

## WakeRecognitionAttempt

**Purpose**: Captures one bounded speech-based wake attempt while the runtime is
in standby.

**Fields**:
- `attempt_id`
- `session_id`
- `selected_wake_mode`: `stt_based_wake`
- `usage_mode`: `standby_wake`
- `capture_profile_id`: `standby_wake.default`
- `timeout_s`
- `language_candidates`
- `cloud_primary_enabled`
- `strict_local_fallback_enabled`
- `network_available`
- `started_at_ms`
- `ended_at_ms`

**Validation Rules**:
- `timeout_s` must be positive and must not exceed `7.0`.
- `selected_wake_mode` is `stt_based_wake` for Phase 19 speech wake attempts.
- When cloud is disabled, the attempt must preserve prior non-cloud behavior.
- The attempt remains valid during network loss if strict local fallback is
  still available.

**Relationships**:
- Consumes one `WakePhraseHintSet`.
- Produces zero or more `WakeRecognitionCandidate` records.
- May produce one `StrictWakeFallbackOutcome`.

## WakeRecognitionCandidate

**Purpose**: Represents one speech wake candidate returned by cloud primary or
strict local fallback before the runtime decides wake accepted, rejected, or
missed.

**Fields**:
- `attempt_id`
- `recognition_source`: `cloud_primary | wake_strict_vosk_fallback |
  cloud_unavailable`
- `status`: `recognized | noncanonical | empty_result | unavailable | failed |
  no_match`
- `primary_transcript`
- `matched_canonical_alias`
- `canonical_gate_passed`
- `command_suffix_ignored`
- `confidence_available`
- `confidence_score`
- `alternative_transcripts`
- `selected_language`
- `detected_language`
- `failure_reason_code`
- `latency_ms`
- `field_safe`
- `raw_user_content_present`

**Validation Rules**:
- `canonical_gate_passed=true` requires a non-empty
  `matched_canonical_alias`.
- A recognized transcript is not automatically accepted wake unless the
  canonical gate passes.
- `command_suffix_ignored=true` is allowed only when a canonical wake alias is
  present and additional tokens are dropped from execution.
- `failure_reason_code` is required for `unavailable`, `failed`, `empty_result`,
  and `no_match` outcomes.
- Default diagnostics must keep `field_safe=true` and
  `raw_user_content_present=false`.

**Relationships**:
- Produced by `WakeRecognitionAttempt`.
- Consumed by `WakeFallbackDecision`.
- Summarized by `StandbyWakeOutcome`.

## StrictWakeFallbackOutcome

**Purpose**: Captures the result of the strict local Vosk wake grammar attempt
after cloud primary fails or returns a non-canonical wake transcript.

**Fields**:
- `attempt_id`
- `fallback_mode`: `wake_grammar`
- `status`: `matched | no_match | unavailable | failed`
- `grammar_phrases`
- `matched_phrase`
- `canonical_wake_alias`
- `confidence_available`
- `confidence_score`
- `detected_language`
- `failure_reason_code`
- `latency_ms`
- `allow_freeform`

**Validation Rules**:
- `allow_freeform` must always be `false`.
- `status=matched` requires `matched_phrase` to exist in `grammar_phrases`.
- `status=no_match` must not expose a usable transcript.
- Non-wake and command-only phrases must resolve to `no_match`, not soft
  acceptance.

**Relationships**:
- Triggered by `WakeFallbackDecision`.
- May be adapted into a `WakeRecognitionCandidate` only when matched.

## WakeFallbackDecision

**Purpose**: Explains whether strict local wake fallback should run after the
cloud-primary wake attempt and how the final source classification is chosen.

**Fields**:
- `decision_id`
- `cloud_status`
- `fallback_enabled`
- `fallback_attempted`
- `fallback_reason`: `cloud_timeout | cloud_unavailable | cloud_empty_result |
  cloud_noncanonical | cloud_failed`
- `selected_source`
- `result_status`: `wake_accepted | wake_rejected | wake_missed`
- `field_safe`

**Validation Rules**:
- Fallback may run only when speech wake is enabled and local strict fallback
  is configured.
- Fallback must run for cloud failures, empty results, and non-canonical cloud
  transcripts.
- Fallback must not run after a canonical wake has already been accepted.
- If cloud and strict fallback both fail to produce a canonical wake, the
  result must be `wake_missed`.

**Relationships**:
- Consumes `WakeRecognitionCandidate` and `StrictWakeFallbackOutcome`.
- Produces the source and outcome inputs for `StandbyWakeOutcome`.

## StandbyWakeOutcome

**Purpose**: Standardizes the structured runtime result emitted after standby
evaluates a wake attempt.

**Fields**:
- `trigger`: `wake_policy`
- `status`: `wake_accepted | wake_rejected | wake_missed | degraded_standby`
- `spoken_text`
- `error_code`
- `next_runtime_state`
- `selected_wake_mode`
- `attempt_source_mode`
- `source_classification`
- `canonical_wake_alias`
- `command_suffix_ignored`
- `payload`

**Validation Rules**:
- `wake_accepted` requires `next_runtime_state=wake` or `listening`.
- `wake_rejected` is reserved for non-canonical or otherwise disallowed wake
  attempts.
- `wake_missed` is reserved for cloud-plus-fallback exhaustion without a
  canonical wake.
- `command_suffix_ignored=true` must never enqueue command execution from the
  same utterance.

**Relationships**:
- Derived from `WakeRecognitionAttempt` and `WakeFallbackDecision`.
- Emitted by `core/assistant_runtime.py`.
- Recorded by field-safe diagnostics and latency metrics.

## State Transitions

- `standby -> wake_policy_selected -> speech_wake_attempt_started` when
  `stt_based_wake` is selected.
- `speech_wake_attempt_started -> cloud_primary_candidate` when cloud wake is
  enabled and available.
- `cloud_primary_candidate -> wake_accepted` when the canonical gate passes.
- `cloud_primary_candidate -> strict_local_wake_fallback` when the cloud
  result is unavailable, failed, empty, or non-canonical.
- `strict_local_wake_fallback -> wake_accepted` when the strict grammar matches
  an approved wake alias and the canonical gate passes.
- `strict_local_wake_fallback -> wake_missed` when no canonical wake is found
  and standby safely resumes.
- `keyword_low_power | hardware_trigger -> wake_accepted` remain valid existing
  transitions outside the speech wake path and must not regress.
