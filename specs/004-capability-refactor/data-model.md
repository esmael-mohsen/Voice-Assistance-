# Data Model: Capability Refactor

## CapabilityDescriptor

- **Purpose**: Defines one runtime capability, its migration state, supported
  actions, backend classification, and fallback policy.
- **Fields**:
  - `capability_id`: canonical identifier such as `obstacle_detection`,
    `ocr`, `system_status`, `money_detection`, `face_recognition`, or
    `emotion_recognition`
  - `display_name`: short human-readable label for logs and diagnostics
  - `migrated`: boolean indicating whether the capability now uses its own
    dedicated handler
  - `backend_mode`: `real | fallback | test_double`
  - `supported_actions`: set containing any of `start | stop | execute | status`
  - `fallback_policy`: `disabled | unmigrated_only | test_only`
  - `requires_network`: boolean
  - `dependency_name`: adapter or provider label used by the capability
  - `timeout_policy_id`: foreign key to `CapabilityTimeoutPolicy`
- **Validation Rules**:
  - `capability_id` must be unique
  - `migrated=true` with `backend_mode=real` implies `fallback_policy=disabled`
    for production runtime behavior
  - `supported_actions` must not be empty
  - `fallback_policy=test_only` may only be enabled in explicit test or debug
    composition
- **Relationships**:
  - owns many `CapabilityActionBinding` records
  - uses one `CapabilityTimeoutPolicy`
  - produces `CapabilityStatusSnapshot`

## CapabilityActionBinding

- **Purpose**: Maps an existing command intent to the capability action that
  should be invoked.
- **Fields**:
  - `intent_id`: existing parser intent such as `enable_obstacle_detection`
  - `capability_id`
  - `action`: `start | stop | execute | status`
  - `default_params`: optional parameter defaults injected by resolver
  - `allows_follow_up_context`: boolean for flows like face to emotion
- **Validation Rules**:
  - `intent_id` must map to exactly one capability action in this phase
  - `action` must be present in the target descriptor's `supported_actions`
- **Relationships**:
  - links command parsing output to `CapabilityRequest`

## CapabilityRequest

- **Purpose**: Represents one runtime request for capability work after command
  resolution.
- **Fields**:
  - `request_id`
  - `capability_id`
  - `action`
  - `params`: normalized machine-readable parameter map
  - `source_mode`: `console | gui | test`
  - `issued_at`
  - `timeout_seconds`
  - `correlation_id`: runtime trace or event correlation value
- **Validation Rules**:
  - `timeout_seconds` must come from the selected `CapabilityTimeoutPolicy`
  - `params` must be JSON-serializable or safely representable in logs
  - `action` must be supported by the target descriptor
- **Relationships**:
  - dispatched to one capability handler
  - produces one `CapabilityResult`

## CapabilityResult

- **Purpose**: Normalized structured outcome returned by a capability handler
  after `start`, `stop`, or `execute`.
- **Fields**:
  - `request_id`
  - `capability_id`
  - `action`
  - `status`: `success | unavailable | timeout | failed | rejected`
  - `spoken_text`
  - `payload`: machine-readable state or result data
  - `error_code`: optional code such as `capability_timeout`,
    `dependency_unavailable`, `invalid_action`, or `capability_failure`
  - `duration_ms`
  - `used_fallback`: boolean
  - `backend_name`
  - `metadata`: optional trace and observability details
- **Validation Rules**:
  - `spoken_text` is required for every result
  - `timeout`, `failed`, and `rejected` statuses require `error_code`
  - `used_fallback=true` is invalid for migrated real capabilities in
    production runtime
  - `payload` must hold machine state; it must not rely on localized strings as
    the only state representation
- **Relationships**:
  - returned to resolver, dispatcher, and runtime observers
  - may update `CapabilityStatusSnapshot`

### Capability Result State Transitions

- `request received + handler success -> success`
- `request received + dependency unavailable -> unavailable`
- `request exceeds timeout -> timeout`
- `request hits handler exception -> failed`
- `unsupported action or invalid policy -> rejected`

## CapabilityStatusSnapshot

- **Purpose**: Machine-readable status view for a capability, with an optional
  short spoken summary for operators.
- **Fields**:
  - `capability_id`
  - `lifecycle_state`: `inactive | starting | active | stopping | failed`
  - `availability`: `ready | degraded | unavailable`
  - `using_fallback`: boolean
  - `backend_name`
  - `last_result_status`
  - `last_error_code`: optional
  - `spoken_summary`: optional short spoken text
  - `details`: structured status details, such as last observation or health
    metadata
- **Validation Rules**:
  - `using_fallback=true` is allowed only for unmigrated or explicit test-only
    capability paths
  - `spoken_summary` must remain optional and brief
  - `details` must stay machine-readable
- **Relationships**:
  - owned by one `CapabilityDescriptor`
  - may embed `ObstacleObservation` in `details`

### Capability Lifecycle Transitions

- `inactive -> start request -> starting -> active`
- `active -> status request -> active`
- `active -> stop request -> stopping -> inactive`
- `starting or active -> timeout or failure -> failed`
- `failed -> successful restart -> active`

## CapabilityTimeoutPolicy

- **Purpose**: Defines bounded execution windows for each supported capability
  action.
- **Fields**:
  - `capability_id`
  - `start_timeout_s`
  - `stop_timeout_s`
  - `status_timeout_s`
  - `execute_timeout_s`
  - `hard_max_s`
- **Validation Rules**:
  - every timeout value must be greater than `0`
  - every timeout value must be less than or equal to `hard_max_s`
  - `hard_max_s` must never exceed `10.0`
  - obstacle detection targets `3.0` seconds or less for supported actions on
    an available backend
- **Relationships**:
  - referenced by `CapabilityDescriptor`
  - applied to `CapabilityRequest`

## ObstacleObservation

- **Purpose**: Carries the first real capability's machine-readable detection
  output.
- **Fields**:
  - `detected`: boolean
  - `distance_meters`: optional float
  - `angle_degrees`: optional float
  - `severity`: `clear | warning | critical`
  - `confidence`: optional float from `0.0` to `1.0`
  - `sensor_source`: backend or adapter label
  - `captured_at`
- **Validation Rules**:
  - `distance_meters` must be non-negative when present
  - `severity=clear` typically pairs with `detected=false`
  - `confidence`, when present, must stay within `0.0` and `1.0`
- **Relationships**:
  - returned in `CapabilityResult.payload`
  - surfaced through `CapabilityStatusSnapshot.details` for obstacle status
