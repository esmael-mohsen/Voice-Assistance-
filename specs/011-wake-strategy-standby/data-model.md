# Data Model: Wake Strategy and Low-Power Standby

## WakeModePolicy

- **Purpose**: Represents the configured rules that determine which wake modes
  are allowed for the current runtime context.
- **Fields**:
  - `primary_mode`: `keyword_low_power | hardware_trigger | stt_based_wake`
  - `fallback_mode`: `keyword_low_power | hardware_trigger | stt_based_wake`
  - `dev_fallback_mode`: `stt_based_wake`
  - `stt_wake_allowed_in_production`: boolean
  - `low_power_standby_enabled`: boolean
  - `runtime_environment`: `production_like | development`
- **Validation Rules**:
  - `primary_mode`, `fallback_mode`, and `dev_fallback_mode` must be supported
    wake modes.
  - `stt_based_wake` is valid in `production_like` mode only when
    `stt_wake_allowed_in_production=true`.
  - `runtime_environment` must be explicit whenever wake policy is resolved.
- **Relationships**:
  - consumed by `WakeSelectionDecision`
  - persisted through existing settings storage

## WakeCapabilitySnapshot

- **Purpose**: Captures which permitted wake sources are actually available at
  the moment standby is entered.
- **Fields**:
  - `provider_id`
  - `keyword_wake_available`: boolean
  - `hardware_trigger_available`: boolean
  - `stt_wake_available`: boolean
  - `provider_availability`: `ready | degraded | unavailable`
  - `network_available`: boolean
- **Validation Rules**:
  - `provider_availability=unavailable` requires at least one wake source to be
    unavailable.
  - Availability must describe current runtime capability, not just stored
    preferences.
- **Relationships**:
  - consumed by `WakeSelectionDecision`
  - recorded in `StandbySession`

## WakeSelectionDecision

- **Purpose**: Defines the concrete wake mode the runtime will honor during one
  standby entry.
- **Fields**:
  - `selected_mode`
  - `fallback_mode`
  - `dev_fallback_mode`
  - `selection_source`: `configured | fallback | dev_fallback | degraded`
  - `fallback_reason`
  - `degraded_mode`: boolean
  - `degraded_reason`
- **Validation Rules**:
  - `selected_mode` must be permitted by `WakeModePolicy`.
  - `selection_source=dev_fallback` requires `selected_mode=stt_based_wake`.
  - `degraded_mode=true` requires a non-empty `degraded_reason`.
- **Relationships**:
  - derived from `WakeModePolicy` and `WakeCapabilitySnapshot`
  - applied to `StandbySession`

## StandbySession

- **Purpose**: Represents one idle assistant window where a chosen wake policy
  remains active until wake, stop, or recovery.
- **Fields**:
  - `session_window_id`
  - `runtime_state`: `standby | wake | listening | error | offline`
  - `selected_wake_mode`
  - `allowed_wake_sources`
  - `degraded_mode`: boolean
  - `degraded_reason`
  - `degraded_guidance_announced`: boolean
  - `wake_cycle_locked`: boolean
- **Validation Rules**:
  - Only one accepted wake cycle may be active per standby session.
  - `degraded_guidance_announced=true` suppresses repeated unchanged degraded
    guidance for that standby entry.
  - `wake_cycle_locked=true` prevents competing wake sources from starting a
    second wake transition.
- **Relationships**:
  - owns `WakeSignalAttempt`
  - emits `StandbyWakeOutcome`

## WakeSignalAttempt

- **Purpose**: Captures how one candidate wake signal was evaluated.
- **Fields**:
  - `attempt_id`
  - `source_mode`: `keyword_low_power | hardware_trigger | stt_based_wake`
  - `raw_signal`
  - `normalized_signal`
  - `accepted`: boolean
  - `rejection_reason`
  - `runtime_environment`
  - `selected_wake_mode`
- **Validation Rules**:
  - `accepted=false` requires a `rejection_reason` when a signal was actually
    observed.
  - `accepted=true` must match the currently selected or otherwise permitted
    wake mode.
  - STT attempts in production-like mode must be rejected when
    `stt_wake_allowed_in_production=false`.
- **Relationships**:
  - belongs to `StandbySession`
  - contributes to `StandbyWakeOutcome`

## StandbyWakeOutcome

- **Purpose**: Standardizes the structured runtime result for accepted,
  rejected, or degraded wake handling.
- **Fields**:
  - `trigger`: `wake_policy`
  - `status`: `wake_accepted | wake_rejected | degraded_standby | unavailable`
  - `spoken_text`
  - `error_code`
  - `next_runtime_state`
  - `selected_wake_mode`
  - `attempt_source_mode`
  - `degraded_mode`
  - `degraded_reason`
  - `payload`
- **Validation Rules**:
  - `wake_accepted` requires `next_runtime_state=wake` or `listening`.
  - `degraded_standby` requires `degraded_mode=true`.
  - `wake_rejected` must preserve a safe standby state.
- **Relationships**:
  - derived from `StandbySession` and `WakeSignalAttempt`
  - measured by `WakeLatencyBaselineRecord`

## WakeLatencyBaselineRecord

- **Purpose**: Captures measurable timing for the approved Phase 11 wake path.
- **Fields**:
  - `measurement_id`
  - `scenario_name`
  - `wake_signal_detected_at`
  - `listening_started_at`
  - `first_response_started_at`
  - `wake_to_listen_ms`
  - `listen_to_response_ms`
  - `cycle_index`
  - `result_bucket`: `within_target | over_target`
- **Validation Rules**:
  - Measurements must use the defined 10-cycle light-load scenario.
  - `wake_to_listen_ms` and `listen_to_response_ms` must be non-negative.
  - `result_bucket=within_target` requires meeting the Phase 11 latency target.
- **Relationships**:
  - associated with accepted `StandbyWakeOutcome`

## Wake State Transitions

- `startup -> standby_waiting -> wake_accepted -> wake -> listening`
- `standby_waiting -> wake_rejected -> standby_waiting`
- `standby_waiting -> degraded_standby -> standby_waiting`
- `standby_waiting -> first_signal_accepted -> wake_cycle_locked`
- `wake_cycle_locked -> competing_signal_ignored -> wake`
- `degraded_standby -> repeated_guidance_without_change` is invalid
