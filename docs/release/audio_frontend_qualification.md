# Audio Front-End Qualification (Phase 14)

## Scope

This report tracks qualification evidence for:

- Capture completeness and bounded relisten behavior
- Local-first and rescue command recognition quality
- Closed-vocabulary constrained flows
- Raspberry Pi 4 latency and demotion decisions

## Recommended Free Local-First Stack

- `SpeechRecognition` for microphone capture
- `Vosk` as preferred local command recognizer
- Legacy compatibility rescue path only on uncertainty
- `core.command_post_processing` for canonical parser input

## Raspberry Pi 4 Tradeoff Policy

- Keep optional enhancements (`rescue`, noise suppression) enabled only if
  qualification budgets are met.
- If budget is exceeded, mark profile `demoted` and publish the simplified
  profile explicitly.

## Evidence Log

### SC-001 Capture Completeness

- Status: `pending`
- Notes: placeholder for clipped-utterance recovery run results.

### SC-002 Local-First Reliability

- Status: `pending`
- Notes: placeholder for noisy local benchmark pass/fail and accuracy.

### SC-003 Rescue Escalation Behavior

- Status: `pending`
- Notes: placeholder for bounded rescue invocation ratio.

### SC-004 Closed-Vocabulary Accuracy

- Status: `pending`
- Notes: placeholder for yes/no and onboarding constrained-flow outcomes.

### SC-005 Qualification Profile Selection

- Status: `pending`
- Notes: placeholder for default vs simplified profile decisions.

### SC-006 Optional Enhancement Demotion

- Status: `pending`
- Notes: placeholder for explicit demotion reasons.

### SC-007 Field-Safe Telemetry

- Status: `pending`
- Notes: placeholder for metadata-only evidence verification.

## Phase 21 STT Rollout Qualification Addendum

The Pi 4 qualification record now includes STT-specific recognition evidence:

- `wake_latency_p95_ms`
- `command_recognition_latency_p95_ms`
- `fallback_latency_p95_ms`
- `cloud_path_memory_mb`
- `fallback_path_memory_mb`
- existing CPU, thermal, uptime, and telemetry completeness metrics

Blocking threshold keys are loaded from `settings/release_thresholds.json`:

- `wake_latency_p95_ms_max`
- `command_recognition_latency_p95_ms_max`
- `fallback_latency_p95_ms_max`
- `cloud_path_memory_mb_max`
- `fallback_path_memory_mb_max`

Pilot and field readiness remain blocked when Pi 4 evidence is missing or when
any threshold budget is breached.
