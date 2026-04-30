# Speech Release Gate Contract

## Purpose

Define the structured release-gate output that combines CI replay validation
with Raspberry Pi 4 qualification evidence.

## Output Shape

```json
{
  "candidate_build_id": "candidate-15",
  "ci_replay_status": "passed",
  "pi_hardware_status": "missing",
  "latest_pi_run_id": null,
  "gate_status": "blocked",
  "approved_for_pilot": false,
  "approved_for_field": false,
  "blocked_reasons": [
    "missing_pi4_qualification"
  ],
  "payload": {
    "telemetry_complete": true,
    "required_artifacts": [
      "telemetry-summary.json",
      "pi-qualification.json"
    ],
    "success_criteria_failures": []
  }
}
```

## Rules

- `approved_for_pilot=true` requires `pi_hardware_status=passed`.
- `approved_for_field=true` requires `approved_for_pilot=true`.
- `gate_status=blocked` requires at least one entry in `blocked_reasons`.
- CI replay may pass while pilot approval still remains blocked for missing or
  failing Raspberry Pi 4 evidence.
- The payload must distinguish artifact completeness from success-criteria
  failures.

## Required Observability Fields

- `candidate_build_id`
- `ci_replay_status`
- `pi_hardware_status`
- `latest_pi_run_id`
- `gate_status`
- `approved_for_pilot`
- `approved_for_field`
- `blocked_reasons`
- `payload.telemetry_complete`
- `payload.required_artifacts`
- `payload.success_criteria_failures`

## Validation Expectations

- Unit coverage for gate-decision rules.
- Integration coverage for CI-pass plus Pi-missing blocked outcomes.
- Smoke or operator validation that release guidance reflects the gate result
  clearly.
