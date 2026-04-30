# STT Rollout Observability Fixtures

This directory contains deterministic field-safe fixtures for Phase 21:

- `stt_events.json`: Event-level telemetry samples.
- `stt_rollups.json`: Per-run telemetry rollup samples.
- `failure_scenarios.json`: Failure taxonomy and bounded recovery outcomes.
- `evidence_index.json`: Release-gate, Pi 4, and PocketSphinx evidence links.

All fixtures are field-safe by default:

- `raw_audio_present` is always `false`.
- `raw_utterance_present` is always `false`.
- Reason codes are machine-readable and do not contain transcript text.
