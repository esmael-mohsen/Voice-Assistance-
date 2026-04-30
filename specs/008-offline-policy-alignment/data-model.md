# Data Model: Offline Truth and Network Policy Alignment

## ProviderConnectivityProfile

- **Purpose**: Defines the approved network dependency truth and fallback
  expectations for one speech provider.
- **Fields**:
  - `provider_id`
  - `display_name`
  - `requires_network`: boolean
  - `supports_wake`: boolean
  - `supports_stt`: boolean
  - `supports_tts`: boolean
  - `fallback_provider_id`: optional
  - `startup_timeout_s`
- **Validation Rules**:
  - `provider_id` must be unique.
  - `requires_network` must describe successful speech-path reality, not just
    wake-word availability.
  - `fallback_provider_id`, when present, must reference another known
    provider.
- **Relationships**:
  - referenced by `ProviderAvailabilitySnapshot`
  - referenced by `OfflinePolicyDecision`

## ConnectivityState

- **Purpose**: Represents the current session-scoped view of general
  connectivity and the effective network state exposed to policy evaluation.
- **Fields**:
  - `override_mode`: `auto | force_offline | force_online`
  - `detected_status`: `online | offline | uncertain`
  - `effective_network_available`: boolean
  - `last_confirmed_status`: `online | offline | unknown`
  - `last_confirmed_at`: optional timestamp
  - `grace_window_deadline_at`: optional timestamp
  - `probe_generation`: integer counter
  - `startup_reset_applied`: boolean
- **Validation Rules**:
  - Every startup must begin with `override_mode=auto`.
  - `force_offline` and `force_online` may change
    `effective_network_available`, but must not erase the underlying
    `detected_status`.
  - `grace_window_deadline_at` is required when `detected_status=uncertain` in
    `auto` mode.
- **Relationships**:
  - updated by `NetworkProbeResult`
  - referenced by `OfflinePolicyDecision`

### Connectivity State Transitions

- `startup_reset -> auto`
- `online -> uncertain_grace -> offline`
- `offline -> uncertain_grace -> online`
- `auto -> force_offline -> auto`
- `auto -> force_online -> auto`

## NetworkProbeResult

- **Purpose**: Captures one connectivity probe attempt that may refresh the
  current `ConnectivityState`.
- **Fields**:
  - `probe_id`
  - `source`: `startup | background | manual`
  - `target_label`
  - `status`: `online | offline | uncertain`
  - `latency_ms`
  - `checked_at`
  - `failure_reason`: optional
- **Validation Rules**:
  - `latency_ms` must be non-negative.
  - `failure_reason` is required for `offline` or `uncertain` results.
- **Relationships**:
  - updates one `ConnectivityState`

## ProviderAvailabilitySnapshot

- **Purpose**: Describes whether the active provider is usable, independent
  from raw network reachability.
- **Fields**:
  - `provider_id`
  - `service_availability`: `ready | degraded | unavailable`
  - `requires_network`: boolean
  - `effective_runtime_ready`: boolean
  - `degraded_reason`: optional
  - `evaluated_at`
- **Validation Rules**:
  - `effective_runtime_ready` must be `false` when
    `service_availability=unavailable`.
  - If `requires_network=true` and `effective_network_available=false`,
    `effective_runtime_ready` must be `false` even when services appear locally
    reachable.
- **Relationships**:
  - belongs to one `ProviderConnectivityProfile`
  - combined with `ConnectivityState` to produce `OfflinePolicyDecision`

## CapabilityOfflineApproval

- **Purpose**: Records explicit approval for whether a capability may execute
  offline or in degraded mode.
- **Fields**:
  - `capability_id`
  - `allowed_offline`: boolean
  - `fallback_mode`: `none | on_device_fallback`
  - `safe_refusal_surface_id`
  - `fallback_status`: optional short label
  - `notes`: optional
- **Validation Rules**:
  - `capability_id` must be unique.
  - `allowed_offline=true` requires `fallback_mode=on_device_fallback`.
  - Non-allowlisted capabilities must still define the safe-refusal surface
    used for truthful guidance.
- **Relationships**:
  - referenced by `OfflinePolicyDecision`

## OfflinePolicyDecision

- **Purpose**: Represents one startup or command-level decision about whether
  execution may proceed, must degrade, or must refuse safely.
- **Fields**:
  - `decision_id`
  - `flow`: `startup | command`
  - `capability_id`: optional
  - `provider_id`
  - `override_mode`
  - `detected_status`
  - `effective_network_available`: boolean
  - `provider_availability`
  - `requires_network`: boolean
  - `offline_allowlisted`: boolean
  - `decision`:
    `allow_execution | on_device_fallback | safe_refusal | provider_degraded | offline_startup`
  - `error_code`: optional
  - `spoken_surface_id`
  - `evaluated_at`
- **Validation Rules**:
  - `safe_refusal`, `provider_degraded`, and `offline_startup` require both
    `error_code` and `spoken_surface_id`.
  - `on_device_fallback` requires `offline_allowlisted=true`.
  - `allow_execution` may not be emitted when `requires_network=true`,
    `effective_network_available=false`, and no approved offline fallback
    exists.
- **Relationships**:
  - references one `ConnectivityState`
  - references one `ProviderAvailabilitySnapshot`
  - references one `ProviderConnectivityProfile`
  - may reference one `CapabilityOfflineApproval`
