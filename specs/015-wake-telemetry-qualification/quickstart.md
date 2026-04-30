# Quickstart: Wake Reliability, Telemetry, and Raspberry Pi Performance Qualification

## Goal

Validate that the assistant wakes quickly and safely, coordinates prompt
playback and listening without weakening risky-command protections, emits
lightweight structured telemetry, and blocks pilot-style releases unless the
latest Raspberry Pi 4 qualification evidence proves the candidate build stays
within wake, latency, stability, and thermal expectations.

## Preconditions

1. Use the project virtual environment and repository root.
2. Ensure the active settings snapshot uses the wake policy profile under test.
3. Keep local artifact output writable for candidate evidence bundles under
   `artifacts/<run-id>/`.
4. Prepare curated replay scenarios for quiet wake, noisy wake, bilingual wake,
   degraded providers, prompt echo, and repeated-fault recovery.
5. Validate headless console mode first; use GUI checks only as a parity pass.
6. Use real Raspberry Pi 4 hardware for final qualification and pilot approval.

## Validation Paths

### 1. Wake Reliability and Confirmation Window

1. Exercise clear supported wake phrases in quiet and representative ambient
   noise conditions.
2. Confirm high-confidence wake detections transition directly to listening.
3. Exercise weak or noisy wake detections and confirm the assistant uses only
   one short confirmation window before promoting or rejecting the wake.

Expected outcome:
- Clear wakes reach listening quickly without unnecessary confirmation.
- Weak or noisy wakes remain bounded and do not trigger indefinite retry loops.
- Production wake behavior stays separated from developer-only fallback paths.

### 2. Safe Barge-In and Protected Prompts

1. Exercise informational, retry, and wake-ready prompts while beginning the
   next valid interaction early.
2. Exercise shutdown, destructive, and explicit confirmation prompts while
   attempting to interrupt them.
3. Confirm the runtime resumes listening early only for prompt classes that are
   allowed to be interrupted safely.

Expected outcome:
- Informational and retry prompts allow natural turn-taking.
- Protected prompts remain uninterruptible until their first spoken pass
  completes.
- Barge-in does not bypass confirmation or risky-command safeguards.

### 3. Ordinary Fault Recovery and Degraded Truthfulness

1. Trigger wake misses, STT failures, provider timeouts, and telemetry sink
   delivery failures.
2. Confirm the assistant stays truthful about degraded behavior and unsupported
   modes.
3. Verify the speech loop resets to standby after the third consecutive
   ordinary fault with one short recovery message.

Expected outcome:
- The assistant never exits unexpectedly during ordinary wake or speech faults.
- Degraded-mode disclosure remains short and accurate.
- Consecutive-fault recovery resets the loop instead of trapping the user in
  repeated retries.

### 4. Telemetry Replay and Evidence Completeness

1. Run quiet, noisy, bilingual, prompt-echo, degraded-provider, and
   repeated-fault replay scenarios through the telemetry path.
2. Confirm wake outcome, wake-to-listen, listen-to-result, and
   result-to-speech-start telemetry are written into local candidate artifacts.
3. Simulate an unavailable external sink and confirm local evidence still
   completes while the export failure is recorded as a recoverable gap.

Expected outcome:
- Telemetry remains lightweight and structured.
- Command-confidence summaries, prompt-echo counts, clarification-loop rate,
  and clipped-utterance retry signals are present in the local evidence bundle.
- Default evidence is stored locally with the candidate artifacts.
- External sink failures never block live interaction or replay validation.

### 5. Raspberry Pi 4 Qualification

1. Run the maintained qualification scenario on Raspberry Pi 4 hardware using
   the candidate wake policy and speech runtime profile.
2. Measure standby CPU, wake CPU spike, listening and speaking CPU or memory,
   startup latency, repeated wake-cycle stability, and thermal behavior.
3. Confirm the qualification bundle records telemetry completeness and any
   blocked thresholds.

Expected outcome:
- Qualification evidence is repeatable and easy to review.
- Builds that exceed resource, latency, shutdown, or thermal limits fail the
  qualification run.
- Hardware evidence stays separate from CI replay results.

### 6. Release Gate Decision

1. Run CI replay and contract validation for the candidate build.
2. Attach the latest passing Raspberry Pi 4 qualification bundle.
3. Evaluate the release gate summary for pilot approval readiness.

Expected outcome:
- CI replay alone is never treated as pilot approval.
- Missing or failing Pi evidence blocks pilot or field release.
- Release-gate output clearly lists the blocking reason when approval is denied.

## Suggested Validation Commands

- `python -m pytest tests/unit/test_wake_word_profiles.py tests/unit/test_wake_strategy_runtime.py tests/unit/test_assistant_runtime.py tests/unit/test_tts_engine_interruptions.py -q`
- `python -m pytest tests/integration/test_wake_strategy_modes.py tests/integration/test_wearable_startup_readiness.py tests/integration/test_runtime_offline_behavior.py tests/integration/test_gui_runtime_bridge.py -q`
- `python -m pytest tests/integration/test_speech_telemetry_pipeline.py tests/integration/test_pi_qualification_release_gates.py -q`
- `python -m pytest tests/smoke/test_wake_strategy_quickstart.py tests/smoke/test_runtime_quickstart.py tests/smoke/test_speech_provider_quickstart.py -q`
- `python -m compileall core tests`
- `ruff check .`

## Operator Notes

- Headless runtime remains the reference validation path for wearable behavior.
- Local artifact storage is the default telemetry evidence path; external sinks
  remain optional integrations.
- Protected prompts must not become barge-in safe just to reduce latency.
- Replay validation and Raspberry Pi qualification are both required, but they
  answer different questions and should be reviewed separately.
- Pilot or field approval requires the latest passing Raspberry Pi 4 evidence,
  not just a green CI run.

## Success Criteria Evidence Ledger

- `SC-001` Wake reliability with bounded confirmation behavior: pass via automated validation on April 23, 2026 (`52 passed`)
- `SC-002` Safe standby reset after repeated ordinary faults: pass via automated validation on April 23, 2026 (`80 passed`)
- `SC-003` Telemetry completeness across benchmark and qualification paths: pass via automated validation on April 23, 2026 (`44 passed`)
- `SC-004` Raspberry Pi 4 qualification and release-gate approval evidence: automated gate logic validated on April 23, 2026; physical Raspberry Pi 4 qualification run still required before pilot approval

## Qualification Command Log

- `python -m pytest tests/unit/test_wake_word_profiles.py tests/unit/test_wake_word_canonical.py tests/integration/test_wake_strategy_modes.py tests/integration/test_runtime_modes.py tests/integration/test_wearable_startup_readiness.py tests/smoke/test_wake_strategy_quickstart.py tests/smoke/test_runtime_quickstart.py -q` -> `52 passed, 2 warnings` (April 23, 2026)
- `python -m pytest tests/unit/test_tts_engine_interruptions.py tests/unit/test_wake_strategy_runtime.py tests/unit/test_assistant_runtime.py tests/integration/test_runtime_modes.py tests/integration/test_runtime_offline_behavior.py tests/integration/test_gui_runtime_bridge.py tests/smoke/test_runtime_quickstart.py tests/smoke/test_speech_provider_quickstart.py -q` -> `80 passed, 2 warnings` (April 23, 2026)
- `python -m pytest tests/unit/test_release_gate_models.py tests/unit/test_runtime_contract.py tests/unit/test_release_latency_baselines.py tests/integration/test_speech_telemetry_pipeline.py tests/integration/test_pi_qualification_release_gates.py tests/integration/test_release_gate_pipeline.py tests/smoke/test_wake_strategy_quickstart.py tests/smoke/test_speech_provider_quickstart.py -q` -> `44 passed, 2 warnings` (April 23, 2026)
- `python -m pytest tests/unit/test_wake_word_profiles.py tests/unit/test_wake_word_canonical.py tests/unit/test_wake_strategy_runtime.py tests/unit/test_tts_engine_interruptions.py tests/unit/test_runtime_contract.py tests/unit/test_release_gate_models.py tests/unit/test_assistant_runtime.py tests/unit/test_release_latency_baselines.py -q` -> `73 passed, 2 warnings` (April 23, 2026)
- `python -m pytest tests/integration/test_wake_strategy_modes.py tests/integration/test_runtime_modes.py tests/integration/test_wearable_startup_readiness.py tests/integration/test_runtime_offline_behavior.py tests/integration/test_gui_runtime_bridge.py tests/integration/test_speech_telemetry_pipeline.py tests/integration/test_pi_qualification_release_gates.py tests/integration/test_release_gate_pipeline.py -q` -> `38 passed, 2 warnings` (April 23, 2026)
- `python -m pytest tests/smoke/test_wake_strategy_quickstart.py tests/smoke/test_runtime_quickstart.py tests/smoke/test_speech_provider_quickstart.py -q` -> `27 passed, 2 warnings` (April 23, 2026)
- `python -m compileall core tests` -> success (April 23, 2026)
- `python -m ruff check .` -> `All checks passed!` (April 23, 2026)
