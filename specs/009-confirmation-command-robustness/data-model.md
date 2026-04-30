# Data Model: Confirmation, Clarification, and Command Robustness

## ConfirmationVocabulary

- **Purpose**: Defines approved affirmative, negative, and cancel phrase
  families used to interpret protected confirmations and comparable onboarding
  confirmations.
- **Fields**:
  - `vocabulary_id`
  - `canonical_outcome`: `affirmative | negative | cancel`
  - `language_scope`: `ar | en | shared`
  - `phrase_variants`: ordered list of normalized token or phrase patterns
  - `precedence_rank`: integer where lower is safer
  - `approved_for_protected_commands`: boolean
- **Validation Rules**:
  - `vocabulary_id` must be unique.
  - `precedence_rank` must place `negative` and `cancel` ahead of
    `affirmative` when both match the same utterance.
  - `phrase_variants` must contain only approved normalized patterns, not
    arbitrary fuzzy thresholds.
- **Relationships**:
  - referenced by `DialogInterpretationResult`

## DialogInterpretationResult

- **Purpose**: Captures how one spoken utterance was normalized, matched, and
  reduced into a safe final dialog outcome.
- **Fields**:
  - `raw_utterance`
  - `normalized_utterance`
  - `matched_outcomes`: ordered list of canonical outcomes
  - `final_outcome`:
    `affirmative | negative | cancel | ambiguous | unmatched`
  - `safe_precedence_applied`: boolean
  - `matched_vocabulary_ids`
- **Validation Rules**:
  - `final_outcome=affirmative` is valid only when no higher-precedence
    negative or cancel cue matched.
  - `safe_precedence_applied=true` is required when mixed cues are reduced to a
    non-executing outcome.
  - `ambiguous` and `unmatched` must remain non-executing outcomes.
- **Relationships**:
  - derived from `ConfirmationVocabulary`
  - consumed by `PendingConfirmationState`
  - consumed by `ClarificationSession` when cancel support is available

## PendingConfirmationState

- **Purpose**: Represents a protected action that is waiting for explicit user
  approval before execution.
- **Fields**:
  - `intent_id`
  - `pending_payload`
  - `active_language`
  - `prompt_surface_id`
  - `created_at`
  - `confirmation_attempt_count`
- **Validation Rules**:
  - Protected execution may proceed only while a pending confirmation is active
    and the associated dialog result resolves to `affirmative`.
  - A negative or cancel outcome must clear the pending state.
  - `prompt_surface_id` must refer to an approved confirmation prompt surface.
- **Relationships**:
  - resolved by `DialogInterpretationResult`
  - emits a `DialogOutcomeRecord`

## ClarificationSession

- **Purpose**: Tracks a parameter-required intent that needs one explicit
  supported option before it can continue.
- **Fields**:
  - `intent_id`
  - `required_slot`
  - `supported_options`
  - `attempt_count`
  - `max_attempts`
  - `active_language`
  - `prompt_surface_id`
  - `started_at`
- **Validation Rules**:
  - `max_attempts` must represent one initial prompt plus two retries.
  - `supported_options` must be explicit, currently valid choices for the
    target command.
  - When `attempt_count` reaches `max_attempts` without resolution, the flow
    must end with a safe stop and no settings change.
- **Relationships**:
  - emits a `DialogOutcomeRecord`
  - may consume a `DialogInterpretationResult` for cancel handling

## FollowUpContextState

- **Purpose**: Represents temporary follow-up context from a prior command that
  may be reused only when it is still relevant to the current dialog.
- **Fields**:
  - `source_intent`
  - `target_intent`
  - `remaining_uses`
  - `context_payload`
  - `status`: `active | consumed | cleared`
- **Validation Rules**:
  - Unrelated follow-up context must be cleared when confirmation or
    clarification becomes active.
  - `remaining_uses` must never become negative.
  - `status=cleared` must prevent follow-up reuse for later dialog turns.
- **Relationships**:
  - may be cleared by `PendingConfirmationState`
  - may be cleared by `ClarificationSession`

## DialogOutcomeRecord

- **Purpose**: Standardizes the structured result of one confirmation or
  clarification step for runtime behavior, diagnostics, and regression tests.
- **Fields**:
  - `flow`: `confirmation | clarification`
  - `intent_id`
  - `status`:
    `confirmed | cancelled | clarification_required | clarification_failed | retry_required`
  - `spoken_surface_id`
  - `spoken_text`
  - `error_code`
  - `used_session_context`: boolean
  - `final_outcome`: optional dialog outcome label
- **Validation Rules**:
  - `spoken_surface_id` and `spoken_text` are required whenever the assistant
    speaks guidance or a safe-stop message.
  - `clarification_failed` requires an `error_code`.
  - `confirmed` may not be emitted without a resolved affirmative outcome and
    an active pending confirmation.
- **Relationships**:
  - produced by `PendingConfirmationState`
  - produced by `ClarificationSession`

## Dialog State Transitions

- `idle -> pending_confirmation -> confirmed`
- `idle -> pending_confirmation -> cancelled`
- `idle -> pending_confirmation -> retry_required`
- `idle -> clarification_required -> resolved`
- `idle -> clarification_required -> retry_required -> clarification_failed`
- `follow_up_active -> pending_confirmation` clears unrelated stale follow-up
- `follow_up_active -> clarification_required` clears unrelated stale follow-up
