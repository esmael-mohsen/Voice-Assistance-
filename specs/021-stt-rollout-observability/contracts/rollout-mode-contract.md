# Rollout Mode Contract

## Purpose

Define the rollout state payload used to apply conservative rollout order and
rollback precedence for cloud-primary STT.

## Payload Shape

```json
{
  "state_id": "rollout-state-001",
  "candidate_run_id": "candidate-2026-04-28",
  "requested_mode": "commands_low_risk",
  "effective_mode": "rollback",
  "rollback_override_active": true,
  "rollback_reason_code": "field_validation_incomplete",
  "field_validation_complete": false,
  "user_visible_behavior_changed": false,
  "protected_command_guard": "enabled",
  "pocketsphinx_compatibility_allowed": false,
  "field_safe_metadata": true
}
```

## Rules

- Allowed requested modes are `shadow`, `wake_only`, `commands_low_risk`, and
  `full_cloud_primary`.
- Rollout advancement order is `shadow` -> `wake_only` ->
  `commands_low_risk` -> `full_cloud_primary`.
- If rollback override is active, `effective_mode` must be `rollback`.
- `shadow` mode must not change user-visible behavior.
- Protected-command confirmation and bilingual safety gates must stay enabled
  for user-visible command rollout modes.
- PocketSphinx compatibility must remain disabled by default for production
  rollout evidence.

## Validation Expectations

- Unit tests validate precedence, allowed transitions, and rollback behavior.
- Integration tests prove release validation rejects skipped rollout stages,
  unsafe user-visible behavior in `shadow`, and disabled protection gates.
