# Pi 4 Qualification Snapshot Contract

## Purpose

Define the Raspberry Pi 4 evidence required for pilot and field STT rollout
approval.

## Snapshot Shape

```json
{
  "snapshot_id": "pi4-stt-001",
  "candidate_run_id": "candidate-2026-04-28",
  "environment": "raspberry_pi_4",
  "wake_latency_p95_ms": 930,
  "command_recognition_latency_p95_ms": 1800,
  "fallback_latency_p95_ms": 2200,
  "standby_cpu_median_pct": 17.2,
  "recognition_cpu_peak_pct": 42.0,
  "cloud_path_memory_mb": 214.0,
  "fallback_path_memory_mb": 220.0,
  "peak_temp_c": 72.0,
  "repeated_wake_cycles": 120,
  "unexpected_shutdown_count": 0,
  "telemetry_completeness_ratio": 0.99,
  "threshold_policy_ref": "settings/release_thresholds.json",
  "status": "passed",
  "blocked_thresholds": [],
  "evidence_refs": ["artifacts/pi4-run-001/stt-qualification.json"]
}
```

## Rules

- Pilot and field approval require real Raspberry Pi 4 evidence.
- Missing or failed Pi 4 qualification blocks pilot and field approval.
- Threshold evaluation uses the approved release threshold policy.
- Evidence must report recognition latency and resource metrics for cloud and
  strict fallback paths.

## Validation Expectations

- Unit tests validate threshold comparisons and missing evidence behavior.
- Integration tests prove release gates distinguish CI replay from Pi 4
  approval evidence.
