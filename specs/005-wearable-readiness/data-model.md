# Data Model: Wearable Readiness

## InteractionPriorityEvent

- **Purpose**: Represents one user-visible runtime message candidate before
  speech output.
- **Fields**:
  - `event_id`: unique message identifier
  - `priority`: `warning | action_confirmation | info | error`
  - `message_text`: localized output text selected for the active language
  - `message_key`: canonical key for duplicate detection and analytics
  - `created_at`: event timestamp
  - `expires_at`: optional deadline after which stale output should be dropped
  - `source`: `runtime | capability | provider | onboarding`
  - `coalescing_group`: optional hash/key used to merge duplicates
  - `requires_immediate_delivery`: boolean
- **Validation Rules**:
  - `event_id` must be unique per runtime session
  - `priority` must be one of the defined enum values
  - `message_text` must be non-empty and bounded for wearable delivery
  - `coalescing_group` is required when dedup/coalescing is enabled
- **Relationships**:
  - routed through `PriorityRoutingWindow`
  - may become a `SpeechSessionWindow` output task

## PriorityRoutingWindow

- **Purpose**: Holds pending events for ordering and deduplication.
- **Fields**:
  - `window_id`
  - `coalescing_window_s`: fixed at `2.0`
  - `pending_events`: ordered collection of `InteractionPriorityEvent`
  - `last_flush_at`
- **Validation Rules**:
  - `coalescing_window_s` must equal `2.0` for this feature
  - same-priority duplicates with the same `coalescing_group` created within
    the window must collapse into one output
- **Relationships**:
  - consumes `InteractionPriorityEvent`
  - drives `SpeechSessionWindow` creation

## SpeechSessionWindow

- **Purpose**: Represents a bounded listening or speaking interaction.
- **Fields**:
  - `session_window_id`
  - `session_id`: runtime session foreign key
  - `mode`: `listening | speaking`
  - `started_at`
  - `ended_at`: optional
  - `max_duration_s`
  - `interrupted`: boolean
  - `interrupt_reason`: `stop | cancel | emergency | timeout | runtime_shutdown | none`
  - `completion_status`: `success | timeout | interrupted | failed`
  - `output_event_id`: optional linked `InteractionPriorityEvent`
- **Validation Rules**:
  - `max_duration_s` must be > 0
  - `ended_at` is required when `completion_status != success` or session
    closes
  - `interrupt_reason` must be set when `interrupted=true`
- **Relationships**:
  - may be preempted by `InterruptSignal`
  - emits `RuntimeRecoveryOutcome`

### Speech Session State Transitions

- `scheduled -> active -> completed`
- `scheduled -> active -> interrupted`
- `scheduled -> active -> timeout`
- `scheduled -> active -> failed`

## InterruptSignal

- **Purpose**: Captures high-priority preemption intent for active sessions.
- **Fields**:
  - `signal_id`
  - `signal_type`: `stop | cancel | emergency`
  - `issued_at`
  - `source`: `voice | hardware | runtime`
  - `acknowledged_at`: optional
  - `target_window_id`: optional active `SpeechSessionWindow`
- **Validation Rules**:
  - `signal_type` must be one of the defined high-priority values
  - active session should acknowledge the signal within configured budget
    (target: <= 1.0s)
- **Relationships**:
  - preempts `SpeechSessionWindow`
  - produces `RuntimeRecoveryOutcome`

## WakeStrategyProfile

- **Purpose**: Defines wake-mode priority and fallback behavior for standby.
- **Fields**:
  - `profile_id`
  - `primary_mode`: `keyword_low_power`
  - `fallback_mode`: `hardware_trigger`
  - `dev_fallback_mode`: `stt_based_wake`
  - `stt_wake_allowed_in_production`: boolean (must be `false`)
  - `low_power_standby_enabled`: boolean
  - `last_mode_switch_reason`: optional
- **Validation Rules**:
  - `primary_mode` must be `keyword_low_power` for this phase
  - production runtime must reject `stt_based_wake` as default
- **Relationships**:
  - consumed by standby runtime loop
  - referenced by startup readiness checks

## ConnectivityCapabilityProfile

- **Purpose**: Describes whether a provider/capability needs network and how
  offline behavior must be handled.
- **Fields**:
  - `capability_id`
  - `provider_id`
  - `requires_network`: boolean
  - `offline_allowlisted`: boolean
  - `fallback_mode`: `on_device | safe_refusal`
  - `safe_refusal_key`: localized prompt key used when execution is denied
- **Validation Rules**:
  - `requires_network=true` and `offline_allowlisted=false` implies mandatory
    safe refusal in offline mode
  - `offline_allowlisted=true` requires `fallback_mode=on_device`
- **Relationships**:
  - consulted before `SpeechSessionWindow` execution
  - contributes to `RuntimeRecoveryOutcome`

## CriticalPromptRecord

- **Purpose**: Tracks high-consequence bilingual prompts used in onboarding and
  safety flows.
- **Fields**:
  - `prompt_key`
  - `arabic_text`
  - `english_text`
  - `category`: `onboarding | safety | interruption | offline | startup`
  - `integrity_status`: `valid | corrupted | replaced`
  - `fallback_prompt_key`: optional
  - `last_validated_at`
- **Validation Rules**:
  - both language fields must be non-empty when `integrity_status=valid`
  - corrupted prompts must not be sent directly to TTS
- **Relationships**:
  - consumed by localized output rendering
  - failures produce `RuntimeRecoveryOutcome`

## StartupReadinessSnapshot

- **Purpose**: Machine-readable readiness checkpoint for non-visual startup.
- **Fields**:
  - `session_id`
  - `boot_started_at`
  - `provider_ready_at`: optional
  - `wake_ready_at`: optional
  - `audio_ready_at`: optional
  - `non_visual_ready_at`: optional
  - `startup_status`: `initializing | ready | degraded | offline`
  - `degraded_reason`: optional
- **Validation Rules**:
  - `non_visual_ready_at` required for `startup_status=ready`
  - readiness latency target: <= 8s for >=95% of boots
- **Relationships**:
  - emitted as runtime/system event payload
  - referenced by quickstart acceptance criteria

### Startup Readiness Transitions

- `initializing -> ready`
- `initializing -> degraded`
- `initializing -> offline`
- `degraded -> ready` (if recovery succeeds)

## RuntimeRecoveryOutcome

- **Purpose**: Standardized outcome after interruption, timeout, or degraded
  handling.
- **Fields**:
  - `outcome_id`
  - `trigger`: `interrupt | timeout | offline_policy | provider_failure`
  - `status`: `recovered | safe_refusal | fallback_applied | offline`
  - `spoken_text`
  - `error_code`: optional (`interrupt_applied`, `listen_timeout`,
    `speak_timeout`, `offline_not_allowlisted`, `provider_unavailable`)
  - `duration_ms`
  - `next_runtime_state`
- **Validation Rules**:
  - `spoken_text` is required and must be concise
  - `error_code` required for non-success paths
- **Relationships**:
  - linked to `SpeechSessionWindow` and `ConnectivityCapabilityProfile`
  - surfaced to runtime observability output
