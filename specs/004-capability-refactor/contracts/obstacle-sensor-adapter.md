# Obstacle Sensor Adapter Contract

## Purpose

Define the adapter boundary for the first migrated real capability,
`obstacle_detection`.

## Adapter Responsibilities

The obstacle adapter provides the controller with device or provider-backed
obstacle observations without exposing backend-specific details to resolver or
runtime layers.

## Required Operations

- `is_available() -> bool`
- `start_monitoring() -> None`
- `stop_monitoring() -> None`
- `read_observation(timeout_s: float) -> ObstacleObservation | None`
- `describe_health() -> dict[str, Any]`

## Observation Shape

`read_observation()` should produce machine-readable data equivalent to:

```json
{
  "detected": true,
  "distance_meters": 1.2,
  "angle_degrees": 45.0,
  "severity": "warning",
  "confidence": 0.93,
  "sensor_source": "camera_depth_adapter",
  "captured_at": "2026-04-18T12:00:00Z"
}
```

## Behavioral Rules

- If `is_available()` is `false`, the obstacle controller must return an
  explicit unavailable result and must not silently fall back to
  `mock_controllers`.
- `read_observation(timeout_s)` must honor the timeout budget supplied by the
  capability timeout runner.
- `describe_health()` must be machine-readable and suitable for status payloads
  and structured logs.
- Test doubles may implement the same adapter contract for unit and integration
  tests.

## Degraded and Weak-Dependency Behavior

- The Phase 4 plan assumes obstacle detection is local-sensor-first and does
  not require network access by default.
- If a future obstacle backend requires network or a remote provider, the
  adapter must surface that dependency through `describe_health()` and the
  controller must return safe unavailable or timeout outcomes under weak
  network conditions.
- No obstacle runtime failure may block the assistant beyond the configured
  timeout or the `10.0` second hard cap.

## Validation Expectations

- Unit tests verify availability, success, unavailable, and timeout paths.
- Integration tests verify obstacle controller results stay stable whether the
  adapter succeeds, fails, or times out.
- Smoke validation confirms GUI and console flows surface the same spoken and
  machine-readable outcomes.

## Implementation Notes (2026-04-18)

- The current migrated implementation provides:
  - `LocalObstacleSensorAdapter` as the default local-sensor-first adapter.
  - `ObstacleCapabilityController` as the first real capability boundary.
  - `FakeObstacleAdapter` test double in `tests/conftest.py` for deterministic
    failure and timeout scenarios.
- Adapter status is surfaced in machine-readable health details so resolver and
  runtime can emit stable failure outcomes without relying on spoken text.
- Timeout behavior is enforced through shared timeout helpers in
  `controllers/capability_contracts.py`, with controller-level safe failures
  for timeout and unavailable states.
