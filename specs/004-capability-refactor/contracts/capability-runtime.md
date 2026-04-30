# Capability Runtime Contract

## Purpose

Define the runtime-facing contract for migrated and unmigrated capabilities
during the Phase 4 capability refactor.

## Capability Surface

The runtime continues to accept the existing command intents, but resolver maps
them to capability actions:

| Intent | Capability ID | Action |
|---|---|---|
| `enable_obstacle_detection` | `obstacle_detection` | `start` |
| `disable_obstacle_detection` | `obstacle_detection` | `stop` |
| `get_system_status` | `system_status` | `status` |
| `enable_OCR` | `ocr` | `start` |
| `disable_OCR` | `ocr` | `stop` |
| `enable_money_detection` | `money_detection` | `start` |
| `disable_money_detection` | `money_detection` | `stop` |
| `recognize_face` | `face_recognition` | `execute` |
| `recognize_emotion` | `emotion_recognition` | `execute` |

## Handler Interface Contract

Each registered capability handler may implement any supported subset of these
operations:

- `start(request) -> CapabilityResult`
- `stop(request) -> CapabilityResult`
- `execute(request) -> CapabilityResult`
- `get_status(request) -> CapabilityStatusSnapshot`

Handlers must advertise supported actions through `CapabilityDescriptor`.
Resolver and registry must not call unsupported actions.

## CapabilityRequest Shape

```json
{
  "request_id": "cap-req-001",
  "capability_id": "obstacle_detection",
  "action": "start",
  "params": {},
  "source_mode": "console",
  "timeout_seconds": 3.0,
  "correlation_id": "runtime-abc123"
}
```

## CapabilityResult Shape

Every `start`, `stop`, or `execute` operation returns:

```json
{
  "request_id": "cap-req-001",
  "capability_id": "obstacle_detection",
  "action": "start",
  "status": "success",
  "spoken_text": "Obstacle detection enabled.",
  "payload": {
    "lifecycle_state": "active",
    "using_fallback": false
  },
  "error_code": null,
  "duration_ms": 420,
  "used_fallback": false,
  "backend_name": "obstacle_sensor",
  "metadata": {
    "timeout_seconds": 3.0
  }
}
```

## CapabilityStatusSnapshot Shape

Status operations return:

```json
{
  "capability_id": "obstacle_detection",
  "lifecycle_state": "active",
  "availability": "ready",
  "using_fallback": false,
  "backend_name": "obstacle_sensor",
  "last_result_status": "success",
  "last_error_code": null,
  "spoken_summary": "Obstacle detection is active.",
  "details": {
    "detected": false,
    "severity": "clear"
  }
}
```

## Result Rules

- `spoken_text` is required for every `CapabilityResult`.
- `status` must be one of `success`, `unavailable`, `timeout`, `failed`, or
  `rejected`.
- `error_code` is required for `unavailable`, `timeout`, `failed`, and
  `rejected`.
- `payload` and `details` must hold machine-readable state and must not depend
  on localized spoken strings as the only state representation.
- GUI and console callers must receive equivalent result shape and status
  semantics.

## Timeout Rules

- Every capability action uses the timeout from `CapabilityTimeoutPolicy`.
- No action may exceed the global hard maximum of `10.0` seconds.
- Obstacle detection should target `3.0` seconds or less for `start`, `stop`,
  and `status` on an available backend.
- Timeout expiration must produce a `CapabilityResult` with:
  - `status: "timeout"`
  - `error_code: "capability_timeout"`
  - brief spoken recovery guidance

## Fallback Rules

- Fallback is allowed only for unmigrated or explicit test-only capabilities.
- Migrated real capabilities must not invoke fallback when their backend fails
  at runtime.
- Any fallback execution must be explicit in both registry metadata and result
  fields:
  - `used_fallback: true`
  - `payload.using_fallback: true` or `using_fallback: true` in status
- Production runtime must reject a migrated capability configuration that would
  silently fallback on runtime failure.

## Error Codes

Recommended error codes for Phase 4:

- `capability_timeout`
- `capability_unavailable`
- `dependency_unavailable`
- `invalid_action`
- `capability_failure`
- `fallback_not_allowed`

## Observability Contract

Each capability invocation should emit structured log fields equivalent to:

```json
{
  "capability_id": "obstacle_detection",
  "action": "start",
  "status": "success",
  "backend_name": "obstacle_sensor",
  "used_fallback": false,
  "duration_ms": 420,
  "error_code": null
}
```

## Validation Expectations

- Contract tests verify stable result and status shapes across success,
  unavailable, timeout, and failure outcomes.
- Runtime integration tests verify GUI or console parity for migrated
  capability behavior.
- Smoke validation confirms unmigrated capabilities can still use explicit
  fallback while migrated capabilities safe-fail.

## Implementation Notes (2026-04-18)

- Runtime contract is implemented through:
  - `controllers/capability_contracts.py`
  - `controllers/capability_registry.py`
  - `controllers/obstacle_controller.py`
  - `core/resolver.py`
  - `core/dispatcher.py`
  - `core/assistant_runtime.py`
- Migrated obstacle behavior is enforced as `backend_mode=real` with
  `fallback_policy=disabled`; fallback attempts for migrated real capability
  paths are rejected with `fallback_not_allowed`.
- Unmigrated OCR, money detection, face recognition, emotion recognition, and
  system status remain available through explicit fallback handlers with
  `used_fallback: true`.
- Dispatch payloads include `capability_id` and `used_fallback` to keep mode
  parity assertions and downstream runtime consumers machine-safe.
