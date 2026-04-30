# Data Model: Interrupt Safety and TTS Preemption

## InterruptVocabulary

- **Purpose**: Defines the approved Arabic and English safety phrases that may
  trigger an interrupt.
- **Fields**:
  - `vocabulary_id`
  - `signal_type`: `stop | cancel | emergency`
  - `language_scope`: `ar | en | shared`
  - `phrase_variants`
  - `global_safety_phrase`: boolean
  - `priority_rank`
- **Validation Rules**:
  - `vocabulary_id` must be unique.
  - `phrase_variants` must contain only approved normalized phrases or tokens.
  - `global_safety_phrase=true` means the phrase remains valid regardless of
    the active prompt language.
- **Relationships**:
  - referenced by `InterruptDetectionResult`

## InterruptDetectionResult

- **Purpose**: Captures how one recognized utterance was evaluated as an
  interrupt candidate.
- **Fields**:
  - `raw_utterance`
  - `normalized_utterance`
  - `matched_vocabulary_ids`
  - `signal_type`: `stop | cancel | emergency | none`
  - `accepted`: boolean
  - `active_runtime_state`
  - `active_language`
- **Validation Rules**:
  - `accepted=true` requires a non-`none` `signal_type`.
  - Unmatched or unrelated text must produce `accepted=false`.
  - Detection must not depend exclusively on the current prompt language.
- **Relationships**:
  - derived from `InterruptVocabulary`
  - consumed by `SpeechPlaybackSession`
  - consumed by `InFlightOperationContext`

## SpeechPlaybackSession

- **Purpose**: Represents one bounded spoken-output session that may be
  interrupted while audio is already playing.
- **Fields**:
  - `session_window_id`
  - `started_at`
  - `ended_at`
  - `prompt_surface_id`
  - `spoken_text`
  - `playback_state`: `queued | speaking | interrupted | completed | timeout`
  - `interrupt_reason`
  - `provider_id`
- **Validation Rules**:
  - A session in `speaking` must transition to exactly one terminal state.
  - `playback_state=interrupted` requires an `interrupt_reason`.
  - Terminal playback must not resume automatically after an accepted
    interrupt.
- **Relationships**:
  - may emit a `PreemptionOutcome`
  - measured by `PreemptionLatencyRecord`

## InFlightOperationContext

- **Purpose**: Tracks the currently active assistant work that may need
  cancellation or best-effort interruption.
- **Fields**:
  - `operation_id`
  - `intent_id`
  - `capability_id`
  - `runtime_state`
  - `reversible`: boolean
  - `cancellation_state`: `idle | cancel_requested | cancelled | best_effort_only | completed`
  - `follow_on_work_suppressed`: boolean
- **Validation Rules**:
  - `cancelled` is valid only when the operation is still reversible.
  - `best_effort_only` is required when the operation has crossed a
    non-reversible point but speech and follow-on work can still be stopped.
  - `follow_on_work_suppressed=true` must prevent new assistant output from the
    interrupted flow.
- **Relationships**:
  - receives an `InterruptDetectionResult`
  - emits a `PreemptionOutcome`

## PreemptionOutcome

- **Purpose**: Standardizes the machine-readable result of an accepted or
  ignored interrupt.
- **Fields**:
  - `trigger`: `interrupt`
  - `status`: `recovered | ignored | best_effort_only | failed`
  - `spoken_text`
  - `error_code`
  - `completion_status`: `interrupted | ignored | partial | failed`
  - `interrupt_signal_type`
  - `next_runtime_state`
  - `provider_id`
  - `capability_id`
- **Validation Rules**:
  - Accepted interrupts require `interrupt_signal_type`.
  - `completion_status=interrupted` requires a safe next runtime state.
  - `completion_status=partial` indicates speech stopped but the underlying
    operation may already be completing.
- **Relationships**:
  - produced from `SpeechPlaybackSession`
  - produced from `InFlightOperationContext`
  - measured by `PreemptionLatencyRecord`

## PreemptionLatencyRecord

- **Purpose**: Captures timing between interrupt acceptance and effective
  speech or work stoppage.
- **Fields**:
  - `measurement_id`
  - `interrupt_detected_at`
  - `preemption_completed_at`
  - `preemption_latency_ms`
  - `latency_target_bucket`: `within_target | over_target | over_ceiling`
  - `runtime_load_profile`: `normal | moderate`
- **Validation Rules**:
  - `preemption_latency_ms` must be non-negative.
  - `within_target` means the interrupt completed within 500 ms.
  - `over_ceiling` means the interrupt exceeded 1 second and must fail the
    release gate.
- **Relationships**:
  - associated with `PreemptionOutcome`
  - associated with `SpeechPlaybackSession`

## Interrupt State Transitions

- `idle -> detected_unmatched -> ignored`
- `speaking -> interrupt_detected -> playback_interrupted -> standby`
- `thinking -> interrupt_detected -> operation_cancel_requested -> standby`
- `thinking -> interrupt_detected -> best_effort_only -> standby`
- `speaking -> interrupt_detected -> playback_timeout` is invalid for accepted
  interrupt paths
