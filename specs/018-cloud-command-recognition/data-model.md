# Data Model: Cloud-Primary Command Recognition and Safety-Aware Fallback

## CommandRecognitionCandidate

**Purpose**: Represents one command-mode candidate produced by cloud primary,
strict fallback, or an existing compatible local path before command policy
decides execute, confirm, retry, fallback, defer, or refuse.

**Fields**:
- `session_id`: Runtime session or command-turn identifier.
- `recognition_path`: `local_first | rescue | fallback`.
- `provider_id`: Current speech provider identifier, preserving existing
  runtime compatibility.
- `recognition_source`: `cloud_primary | strict_vosk_fallback |
  rescue_strict_vosk | cloud_unavailable | local_vosk | sphinx_compat |
  legacy_local`.
- `primary_transcript`: Candidate transcript text, empty only when an error or
  no-usable-transcript outcome is present.
- `alternative_transcripts`: Ordered tuple of alternative transcripts.
- `confidence_available`: Whether provider confidence was supplied or
  estimated.
- `confidence_score`: Optional normalized confidence value from `0.0` to `1.0`.
- `confidence_band`: `high | medium | low | missing_confidence` as interpreted
  by existing runtime policy.
- `selected_language`: Profile/runtime language used for the recognition
  attempt.
- `detected_language`: Provider-detected language metadata, if available.
- `language_candidates`: Candidate language tuple passed into recognition.
- `endpoint_quality_hints`: Capture quality hints such as clipping indicators.
- `failure_reason_code`: Stable cloud or strict fallback failure code, if any.
- `latency_ms`: Non-negative recognition latency.
- `field_safe`: `true` for diagnostics-safe metadata.
- `raw_user_content_present`: `false` for default diagnostics and artifacts.

**Validation Rules**:
- Successful candidates require a non-empty `primary_transcript`.
- `confidence_score` must be absent unless `confidence_available=true`.
- `confidence_score`, when present, must be between `0.0` and `1.0`.
- `detected_language` must not mutate profile language.
- Raw STT output must not execute without parser and runtime policy.
- `sphinx_compat` may appear only when compatibility is explicitly enabled.

**Relationships**:
- Created from Phase 17 `CloudRecognitionCandidate`, strict Vosk fallback, or
  compatible local recognition.
- Adapted into or represented by `CommandRecognitionResult`.
- Consumed by post-processing, parser, confidence policy, diagnostics, and
  command fallback decision logic.

## CommandPhraseHintSet

**Purpose**: Defines the bounded, deterministic phrase inventory used to bias
cloud command recognition and strict fallback grammars toward approved commands.

**Fields**:
- `phrase_hint_set_id`: Stable identifier such as `command.default`.
- `mode`: `command`.
- `language_scope`: `english | arabic | bilingual`.
- `source_catalogs`: Ordered list of approved catalogs.
- `variant_types`: `canonical | english | arabic | bilingual | phonetic |
  stt_mistake`.
- `priority_order`: Ordered priority categories used when the set reaches its
  maximum size.
- `max_cloud_phrases`: Default `72`.
- `max_strict_grammar_phrases`: Default `220`.
- `phrases`: Stable, deduplicated phrase tuple.
- `raw_user_content_present`: `false` by default.

**Validation Rules**:
- Phrase order must be deterministic for identical source catalogs.
- Empty and duplicate phrases must be removed after normalization.
- Raw user utterance history must not be included by default.
- Protected and safety-critical commands must remain high priority.
- Cloud hints and strict grammar may share the same source catalogs but apply
  their own caps.

**Relationships**:
- Built from parser catalog keywords, closed vocabulary where relevant,
  curated assistive commands, Arabic variants, bilingual/phonetic variants,
  and safety-critical commands.
- Referenced by cloud recognition attempts and strict fallback contracts.

## StrictCommandFallbackOutcome

**Purpose**: Captures the result of a bounded strict Vosk command grammar
attempt after cloud primary fails or runtime policy requests rescue.

**Fields**:
- `fallback_mode`: `command_inventory | closed_choice | wake_grammar`.
- `usage_mode`: `command | confirmation | onboarding`.
- `status`: `matched | no_match | unavailable | failed`.
- `grammar_phrases`: Approved command or closed-vocabulary phrase tuple.
- `matched_phrase`: Approved phrase when matched.
- `primary_transcript`: Matched transcript, absent for no-match/unavailable.
- `confidence_available`: Whether fallback confidence was supplied.
- `confidence_score`: Optional normalized fallback confidence.
- `detected_language`: Metadata language when known.
- `failure_reason_code`: `strict_grammar_no_match |
  strict_vosk_unavailable | strict_vosk_failed`.
- `latency_ms`: Non-negative fallback latency.
- `allow_freeform`: Always `false` for this feature.
- `sphinx_fallback_allowed`: `false` unless explicit compatibility is enabled.

**Validation Rules**:
- `status=matched` requires `matched_phrase` in `grammar_phrases`.
- `status=no_match` must not expose a usable transcript.
- `allow_freeform=false` is mandatory.
- No-match outcomes route to existing retry, confirmation, or safe refusal.

**Relationships**:
- Produced by `core/stt.py` strict fallback logic.
- May become a `CommandRecognitionCandidate` only when matched and parser-safe.
- Feeds `CommandFallbackDecision` and field-safe diagnostics.

## CommandFallbackDecision

**Purpose**: Explains the next safe action after command recognition,
post-processing, parser validation, confidence evaluation, and fallback checks.

**Fields**:
- `decision_id`: Stable diagnostic identifier for the command turn.
- `trigger`: `cloud_timeout | cloud_empty_result | cloud_unavailable |
  cloud_low_confidence | language_mismatch | alternatives_conflict |
  parser_rejected | strict_grammar_no_match | protected_command |
  endpoint_quality`.
- `recognition_source`: Source that triggered the decision.
- `fallback_enabled`: Effective strict fallback setting.
- `fallback_attempted`: Whether strict fallback was attempted.
- `fallback_mode`: Strict fallback mode, if attempted.
- `status_or_decision`: `execute | fallback | confirm | retry | defer |
  refuse | no_usable_transcript`.
- `reason_code`: Stable cloud, strict fallback, or confidence reason.
- `confidence_band`: Existing policy band.
- `field_safe`: Always `true`.
- `raw_user_content_present`: `false` by default.

**Validation Rules**:
- Provider failures cannot produce `execute` directly.
- `strict_grammar_no_match` resolves to `no_usable_transcript`, `retry`,
  `confirm`, or `refuse`, never broad dictation.
- Protected commands cannot resolve to `execute` without explicit affirmative
  confirmation.
- Wake wording cannot increase confidence or bypass validation.

**Relationships**:
- Consumes `CommandRecognitionCandidate`, `StrictCommandFallbackOutcome`, and
  parser/confidence policy outputs.
- Emitted through runtime diagnostics and used by quickstart validation.

## CommandSafetyEvaluation

**Purpose**: Represents the existing runtime policy result that determines
whether a parsed command can execute or needs confirmation, retry, fallback,
defer, or refusal.

**Fields**:
- `parsed_intent_id`: Parser intent identifier, if any.
- `risk_level`: Existing parser/category risk level.
- `requires_confirmation`: Whether protected-command policy requires
  confirmation.
- `confidence_band`: Existing confidence band.
- `alternatives_conflict`: Whether alternatives point to conflicting intents.
- `language_mismatch`: Whether detected language conflicts with command
  context.
- `endpoint_quality_penalty_applied`: Whether clipping or quality hints
  affected confidence.
- `decision_action`: Existing action value.
- `confirmation_required`: Whether explicit confirmation is required before
  execution.
- `fallback_allowed`: Whether rescue or fallback is enabled for the turn.

**Validation Rules**:
- Existing command confidence thresholds remain authoritative.
- Protected commands require confirmation regardless of cloud confidence.
- Low-risk commands may execute only when confidence is high and parser
  acceptance is clean.
- Medium-risk or ambiguous commands must confirm or retry.

**Relationships**:
- Produced by `AssistantRuntime._evaluate_confidence_decision`.
- Consumes command recognition and parser metadata.
- Controls dispatcher/resolver execution.

## RecognitionSourceMetadata

**Purpose**: Provides field-safe source and failure context for headless
diagnostics, tests, and release artifacts.

**Fields**:
- `recognition_source`: Source label.
- `provider_id`: Runtime provider identifier.
- `selected_language`: Profile/runtime selected language.
- `detected_language`: Provider-detected language metadata.
- `fallback_decision`: Fallback status or decision.
- `failure_reason_code`: Stable failure code.
- `latency_ms`: Non-negative latency.
- `latency_category`: `fast | normal | slow | timeout_bound`.
- `field_safe`: Always `true`.
- `raw_user_content_present`: `false` by default.

**Validation Rules**:
- Metadata must not include cloud credential material.
- Metadata must not persist raw utterances by default.
- Source labels must remain compatible with existing command result consumers.

## State Transitions

- `cloud_primary_disabled -> existing_command_path` when rollout is off.
- `cloud_primary_enabled -> cloud_attempt -> cloud_candidate_returned` when
  cloud produces a usable transcript.
- `cloud_candidate_returned -> runtime_policy -> execute` for low-risk,
  high-confidence, parser-clean commands.
- `cloud_candidate_returned -> runtime_policy -> confirm` for protected,
  medium-risk, or ambiguous commands.
- `cloud_candidate_returned -> runtime_policy -> rescue_strict_vosk` when low
  confidence, language mismatch, endpoint quality, alternatives conflict, or
  parser rejection requests fallback.
- `cloud_attempt -> provider_failure -> strict_vosk_fallback` when strict
  fallback is enabled.
- `cloud_attempt -> provider_failure -> no_usable_transcript` when strict
  fallback is disabled.
- `strict_vosk_fallback -> matched -> runtime_policy` when grammar matches an
  approved command.
- `strict_vosk_fallback -> no_match -> existing_recovery` when no approved
  command grammar matches.
- `runtime_policy -> dispatcher_resolver` only after parser and confidence
  gates permit execution.
