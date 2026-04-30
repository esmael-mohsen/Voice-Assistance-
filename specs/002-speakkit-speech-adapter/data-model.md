# Data Model: Speech Abstraction and SpeakKit Adapter

## Speech Provider Profile

- **Purpose**: Represents one provider implementation and its runtime
  capabilities.
- **Fields**:
  - `provider_id`: canonical identifier (`legacy` or `speakkit`)
  - `display_name`: human-readable provider name
  - `supports_wake`: boolean
  - `supports_stt`: boolean
  - `supports_tts`: boolean
  - `requires_network`: boolean
  - `availability`: `ready | degraded | unavailable`
  - `startup_timeout_s`: provider startup-health timeout budget
- **Validation Rules**:
  - `provider_id` must be unique in registry
  - provider is `ready` only if required speech capabilities are available
  - timeout values must be positive
- **Relationships**:
  - referenced by `SpeechProviderSelection`
  - source/target of `FallbackActivationRecord`

## Speech Provider Selection

- **Purpose**: Tracks persisted and session-applied provider choices.
- **Fields**:
  - `persisted_provider`: provider saved in user settings
  - `session_provider`: provider active for current runtime session
  - `selection_source`: `persisted | manual | startup_fallback | default`
  - `pending_provider`: deferred provider switch requested during active session
  - `deferred_until_restart`: boolean
  - `applied_at`: timestamp
- **Validation Rules**:
  - `persisted_provider` and `session_provider` must map to known profiles
  - if runtime is active, provider switch requests set `pending_provider` and
    `deferred_until_restart=true`
  - startup degradation to legacy must not mutate `persisted_provider`
- **Relationships**:
  - links runtime session to one active provider profile
  - produces `SpeechInteractionLifecycleEvent` entries

### Selection State Transitions

- `startup -> load persisted provider`
- `persisted ready -> session provider = persisted`
- `persisted unavailable -> session provider = legacy (temporary degraded mode)`
- `active session switch request -> set pending provider (apply at restart)`
- `restart -> apply pending provider if present`

## Speech Interaction Lifecycle Event

- **Purpose**: Captures provider-aware runtime events for observability and
  validation.
- **Fields**:
  - `session_id`
  - `event_type`: `status | config | error`
  - `stage`: `startup | wake | listening | speaking | shutdown`
  - `active_provider`
  - `fallback_from` (optional)
  - `fallback_to` (optional)
  - `degraded_reason` (optional)
  - `timestamp`
- **Validation Rules**:
  - `active_provider` required for provider-aware `config` and `error` events
  - fallback fields required when fallback occurs
  - degraded reason required for startup temporary legacy fallback

## Fallback Activation Record

- **Purpose**: Tracks each fallback decision and outcome.
- **Fields**:
  - `from_provider`
  - `to_provider`
  - `trigger_stage`: `startup | wake | listening | speaking`
  - `recoverable`: boolean
  - `reason_code`
  - `persisted_provider_unchanged`: boolean
  - `user_notified`: boolean
  - `timestamp`
- **Validation Rules**:
  - `from_provider != to_provider`
  - allowed directional fallback is `speakkit -> legacy` only
  - `persisted_provider_unchanged=true` when startup degrades from unavailable
    persisted provider

## Provider Failure Outcome

- **Purpose**: Normalizes failure classification and required next action.
- **Fields**:
  - `provider_id`
  - `failure_scope`: `startup | runtime`
  - `recoverable`: boolean
  - `next_action`: `fallback | standby_recovery | offline`
  - `manual_restart_required`: boolean
  - `message`
- **Validation Rules**:
  - `next_action=offline` and `manual_restart_required=true` when both
    providers are unavailable
  - legacy runtime recoverable failures must not auto-switch to SpeakKit
  - startup failure of persisted provider with legacy available must use
    `next_action=fallback` to legacy and notify degraded mode
