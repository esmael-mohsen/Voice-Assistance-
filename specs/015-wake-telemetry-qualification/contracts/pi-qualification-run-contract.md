# Pi Qualification Run Contract

## Purpose

Define the machine-readable summary produced by a Raspberry Pi 4 qualification
run for a candidate build.

## Output Shape

```json
{
  "run_id": "pi-run-42",
  "candidate_build_id": "candidate-15",
  "qualification_profile_id": "wake.default",
  "environment": "raspberry_pi_4",
  "status": "failed",
  "metrics": {
    "duration_minutes": 30,
    "standby_cpu_median_pct": 17.2,
    "wake_cpu_peak_pct": 42.0,
    "listen_cpu_peak_pct": 38.5,
    "listen_memory_mb": 214,
    "speak_cpu_peak_pct": 35.1,
    "speak_memory_mb": 220,
    "startup_latency_ms": 3900,
    "peak_temp_c": 83.0,
    "repeated_wake_cycles": 120,
    "unexpected_shutdown_count": 0,
    "telemetry_completeness_ratio": 0.99
  },
  "blocked_thresholds": [
    "standby_cpu_budget",
    "thermal_limit"
  ],
  "evidence_refs": {
    "telemetry_summary": "artifacts/run-42/speech/telemetry-summary.json",
    "startup_doc": "docs/release/startup.md",
    "troubleshooting_doc": "docs/release/troubleshooting.md"
  }
}
```

## Rules

- `environment` must be `raspberry_pi_4` for pilot-approval evidence.
- `status=passed` requires zero `blocked_thresholds`.
- `telemetry_completeness_ratio` must satisfy the declared threshold for a
  passing run.
- All reported resource and latency metrics must be non-negative.
- Evidence references must point to the candidate artifact bundle or release
  documentation associated with the run.

## Required Observability Fields

- `run_id`
- `candidate_build_id`
- `qualification_profile_id`
- `environment`
- `status`
- `metrics.duration_minutes`
- `metrics.standby_cpu_median_pct`
- `metrics.wake_cpu_peak_pct`
- `metrics.listen_cpu_peak_pct`
- `metrics.listen_memory_mb`
- `metrics.speak_cpu_peak_pct`
- `metrics.speak_memory_mb`
- `metrics.startup_latency_ms`
- `metrics.peak_temp_c`
- `metrics.repeated_wake_cycles`
- `metrics.unexpected_shutdown_count`
- `metrics.telemetry_completeness_ratio`
- `blocked_thresholds`

## Validation Expectations

- Integration coverage for qualification summary shaping.
- Replay or fixture coverage for blocked-threshold behavior.
- Real Raspberry Pi 4 execution checks before pilot approval.
