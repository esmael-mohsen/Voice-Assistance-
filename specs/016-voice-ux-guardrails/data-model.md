# Data Model: Continuous Turn-Taking, Closed-Vocabulary Guardrails, and Pilot-Grade Voice UX

## TurnTakingWindow

- **Purpose**: Represents the active guided interaction window that controls
  whether the assistant is speaking only, speaking with barge-in allowed,
  actively listening, listening for a closed-vocabulary answer, waiting for
  confirmation, or recovering after no-input or clipped input.
- **Fields**:
  - `window_id`
  - `session_id`
  - `flow_id`
  - `mode`: `speaking_only | speaking_with_barge_in | listening | closed_vocabulary_listening | waiting_confirmation | recovering`
  - `prompt_surface_id`
  - `prompt_class`
  - `runtime_state`
  - `barge_in_allowed`
  - `global_safety_only_preemption`
  - `closed_vocabulary_id`
  - `opened_at_ms`
  - `closed_at_ms`
  - `recent_prompt_text`
- **Validation Rules**:
  - `window_id`, `session_id`, and `flow_id` must be present.
  - `mode=speaking_with_barge_in` requires `barge_in_allowed=true`.
  - `mode=closed_vocabulary_listening` requires `closed_vocabulary_id`.
  - Protected prompt classes must set `global_safety_only_preemption=true`
    until the first protected prompt pass finishes.
- **Relationships**:
  - references `ClosedVocabularyContext` when guided answers are constrained
  - drives `GuidedDialogSession`
  - may emit `PromptEchoSignal`

## ClosedVocabularyContext

- **Purpose**: Defines the allowed answer space for a guided prompt such as
  language choice, voice gender, speech speed, yes/no/cancel, wake
  confirmation, or retry/help.
- **Fields**:
  - `closed_vocabulary_id`
  - `flow_type`
  - `usage_modes`
  - `allow_mixed_language_aliases`
  - `global_safety_preemption_only`
  - `retry_limit`
  - `safe_fallback_strategy`
  - `option_ids`
  - `retry_surface_ids`
- **Validation Rules**:
  - `closed_vocabulary_id` must be unique within the registry.
  - `retry_limit` must be positive and align with the active settings policy.
  - `safe_fallback_strategy` must be one of
    `keep_default | keep_last_confirmed | discard_candidate | graceful_exit`.
  - `option_ids` must reference at least one `ClosedVocabularyOption`.
- **Relationships**:
  - owns one or more `ClosedVocabularyOption` entries
  - referenced by `TurnTakingWindow`
  - resolved by `GuidedDialogSession`

## ClosedVocabularyOption

- **Purpose**: Represents one accepted canonical answer inside a
  `ClosedVocabularyContext`, including Arabic, English, and mixed alias forms.
- **Fields**:
  - `option_id`
  - `closed_vocabulary_id`
  - `canonical_value`
  - `spoken_value`
  - `alias_tokens`
  - `persisted_value`
  - `requires_confirmation`
- **Validation Rules**:
  - `option_id` must be unique within its parent context.
  - `canonical_value` must be stable enough to use in tests and runtime
    contracts.
  - `alias_tokens` must not overlap another option so broadly that safe
    rejection becomes impossible.
- **Relationships**:
  - belongs to `ClosedVocabularyContext`
  - may become the accepted option in `GuidedDialogSession`

## PromptEchoSignal

- **Purpose**: Captures evidence that recognized speech likely came from the
  assistant's own recent prompt rather than from fresh user input.
- **Fields**:
  - `signal_id`
  - `session_id`
  - `window_id`
  - `prompt_surface_id`
  - `token_overlap_ratio`
  - `timing_offset_ms`
  - `short_answer_exception_applied`
  - `suppressed`
  - `suppressed_at_ms`
- **Validation Rules**:
  - `suppressed=true` requires a non-negative `timing_offset_ms`.
  - `short_answer_exception_applied=true` is valid only when a short approved
    answer remained eligible to pass despite prompt overlap.
  - Suppressed prompt echoes must not consume a retry budget by themselves.
- **Relationships**:
  - emitted during `TurnTakingWindow` evaluation
  - summarized by `PilotVoiceUXEvaluationRun`

## GuidedDialogSession

- **Purpose**: Tracks one guided onboarding, settings, confirmation, or
  recovery flow across accepted answers, rejections, retries, safe defaults,
  and graceful exits.
- **Fields**:
  - `dialog_session_id`
  - `session_id`
  - `flow_type`
  - `current_window_id`
  - `closed_vocabulary_id`
  - `retry_count`
  - `retry_limit`
  - `accepted_option_id`
  - `fallback_strategy_applied`
  - `fallback_reason`
  - `outcome_status`: `accepted | retry_required | prompt_echo_suppressed | rejected | safe_default_applied | graceful_exit`
  - `preserved_safety_state`
- **Validation Rules**:
  - `retry_count` must be between `0` and `retry_limit`.
  - `outcome_status=safe_default_applied` requires `fallback_strategy_applied`.
  - `outcome_status=graceful_exit` requires `fallback_reason`.
  - `accepted_option_id` is required when a closed-vocabulary turn resolves
    successfully.
- **Relationships**:
  - references `TurnTakingWindow`
  - may reference `ClosedVocabularyContext`
  - may own a `NameCandidate`

## NameCandidate

- **Purpose**: Represents a spoken name captured during onboarding that has not
  yet become the accepted final name.
- **Fields**:
  - `candidate_id`
  - `session_id`
  - `raw_candidate_text`
  - `normalized_candidate_text`
  - `capture_quality`
  - `confirmation_status`: `pending | accepted | rejected | discarded`
  - `confirmed_at_ms`
- **Validation Rules**:
  - `confirmation_status=accepted` requires `confirmed_at_ms`.
  - `confirmation_status=accepted` is valid only after an explicit affirmative
    confirmation turn.
  - Rejected or discarded candidates must not be persisted as the final
    username.
- **Relationships**:
  - owned by `GuidedDialogSession`
  - may be summarized by `PilotVoiceUXEvaluationRun`

## PilotVoiceUXEvaluationRun

- **Purpose**: Captures one repeatable spoken-journey validation run used to
  judge whether the pilot-grade voice UX meets completion, retry, and recovery
  expectations.
- **Fields**:
  - `run_id`
  - `scenario_label`
  - `journey_type`
  - `completion_status`: `completed | safe_default_continuation | graceful_exit | failed`
  - `retries_used`
  - `accepted_barge_in_count`
  - `prompt_echo_suppression_count`
  - `out_of_domain_rejection_count`
  - `fallback_or_exit_reason`
  - `raw_utterance_present`
  - `artifact_path`
- **Validation Rules**:
  - `retries_used` must be non-negative.
  - `raw_utterance_present` must be `false` for default field-safe evidence.
  - `completion_status=failed` requires an explicit `fallback_or_exit_reason`.
  - `artifact_path` must point to a local evidence location when a run is
    persisted.
- **Relationships**:
  - aggregates `GuidedDialogSession` outcomes
  - summarizes `PromptEchoSignal` counts
  - provides pilot-readiness evidence for quickstart validation

## State Transitions

- `prompt_selected -> speaking_only -> speaking_with_barge_in` when the prompt
  class is eligible for natural early answers
- `speaking_with_barge_in -> closed_vocabulary_listening` when a guided answer
  window opens
- `closed_vocabulary_listening -> accepted` when a valid option is matched
- `closed_vocabulary_listening -> prompt_echo_suppressed -> closed_vocabulary_listening`
  when captured speech matches recent prompt text
- `closed_vocabulary_listening -> retry_required -> recovering` when input is
  out of domain or missing
- `recovering -> safe_default_applied | graceful_exit` when retry budget is
  exhausted
- `name_candidate_pending -> waiting_confirmation -> accepted` after explicit
  affirmative confirmation
- `name_candidate_pending -> waiting_confirmation -> rejected | discarded` when
  the confirmation turn is negative, cancelled, or uncertain
- `pilot_run_started -> journeys_replayed -> evidence_recorded -> completed | failed`
