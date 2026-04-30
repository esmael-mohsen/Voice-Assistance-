# Quickstart: Wake Strategy and Low-Power Standby

## Goal

Validate that standby behavior now honors the configured wake policy, keeps
STT-based wake development-only unless explicitly allowed, degrades safely when
no permitted wake source is available, and records repeatable wake latency
baselines for release readiness.

## Preconditions

1. Use the project virtual environment and repository root.
2. Run validation in console or headless runtime mode as the reference path.
3. Start from a clean standby session for each scenario.
4. Use persisted wake settings that match the scenario being validated.
5. Ensure wake-capable test doubles or hardware stubs can simulate keyword,
   hardware-trigger, and STT wake signals independently.

## Validation Paths

### 1. Production-Like Keyword Wake

1. Configure standby for `keyword_low_power` with
   `stt_wake_allowed_in_production=false`.
2. Enter standby without enabling free-form STT wake.
3. Trigger the approved keyword wake signal.
4. Verify the assistant leaves standby once, enters listening, and emits the
   expected wake readiness feedback.

Expected outcome:
- Standby wakes from the permitted keyword path.
- The runtime does not need open-ended STT monitoring to leave standby.
- Wake selection and acceptance are recorded in structured runtime output.

### 2. Production-Like STT Rejection

1. Keep the same production-like configuration.
2. Speak the STT wake phrase that is allowed only for development fallback.
3. Verify the assistant stays in standby and records the rejection.
4. Confirm no listening or command flow starts.

Expected outcome:
- STT wake is blocked in production-like mode.
- The runtime remains in safe standby.
- A structured rejection reason is available for validation.

### 3. Development STT Wake Fallback

1. Configure standby for a development scenario where STT wake fallback is
   explicitly allowed.
2. Enter standby with the permitted development wake policy active.
3. Speak the approved STT wake phrase.
4. Verify the assistant wakes and records that a development fallback path was
   used.

Expected outcome:
- STT wake succeeds only in the development-allowed scenario.
- Wake outcome data distinguishes development fallback from production wake.

### 4. No Permitted Wake Source Available

1. Configure a standby session where the preferred wake source is unavailable
   and no other permitted source can be used.
2. Enter standby.
3. Verify the assistant emits one degraded standby notification.
4. Keep the degraded condition unchanged and confirm the notification is not
   repeated continuously.

Expected outcome:
- The assistant remains in safe standby.
- Degraded guidance is spoken once per standby entry unless the reason changes
  or recovery occurs.
- No forbidden fallback becomes active automatically.

### 5. Competing Wake Signals

1. Configure a session where more than one permitted wake source can fire.
2. Trigger two valid wake signals close together.
3. Verify the first accepted signal starts the wake cycle.
4. Confirm later competing signals are ignored until the wake cycle completes.

Expected outcome:
- Only one wake transition occurs for the standby entry.
- No duplicate greeting, prompt, or extra listening transition appears.

### 6. Wake Latency Baseline

1. Run 10 sequential wake cycles on an otherwise idle assistant session with
   stable provider availability and no long-running concurrent capability work.
2. Measure wake-to-listening and listening-to-response timing for each cycle.
3. Compare the results with the Phase 11 baseline target.

Expected outcome:
- At least 95% of accepted wake events reach listening within 1.5 seconds.
- At least 95% of successful wake flows begin the first assistant response
  within 2.5 seconds after listening starts.
- Baseline evidence is recorded in the same release-validation path used for
  runtime latency reporting.

### 7. Headless Parity

1. Run the same wake-policy scenarios in the console or headless runtime path.
2. Repeat a smaller subset in the GUI debug path.
3. Compare wake selection, rejection, and degraded outcomes.

Expected outcome:
- Headless and GUI entry points honor the same wake policy.
- Runtime-owned wake behavior remains authoritative across both paths.

## Suggested Validation Commands

- `python -m pytest tests/unit/test_provider_resolver.py tests/unit/test_assistant_runtime.py -q`
- `python -m pytest tests/integration/test_runtime_modes.py tests/integration/test_wearable_startup_readiness.py -q`
- `python -m pytest tests/smoke/test_runtime_quickstart.py tests/smoke/test_wearable_readiness_quickstart.py -q`
- `python -m compileall core tests`

## Operator Notes

- Production-like standby must not quietly degrade into STT wake when the
  policy forbids it.
- One-time degraded standby guidance is part of the user experience and must
  stay bounded for non-visual use.
- Wake timing evidence should be captured from the runtime path the wearable
  build is expected to use, not only from GUI-driven checks.

## Validation Evidence (2026-04-21)

- **SC-001 (production-like STT rejection + permitted wake only)**:
  `python -m pytest tests/integration/test_runtime_modes.py tests/integration/test_wearable_startup_readiness.py tests/integration/test_wake_strategy_modes.py -q` passed (15 tests).
- **SC-004 / SC-004a / SC-004b (safe degraded standby, one-time degraded guidance, weak-network truthfulness)**:
  `python -m pytest tests/unit/test_wake_strategy_runtime.py tests/integration/test_runtime_offline_behavior.py tests/integration/test_wake_strategy_modes.py tests/smoke/test_wake_strategy_quickstart.py -q` passed (18 tests).
- **SC-002 / SC-003 / SC-005 (wake readiness regressions and release-facing baseline checks)**:
  `python -m pytest tests/unit/test_release_latency_baselines.py tests/integration/test_release_latency_pipeline.py tests/integration/test_release_journey_validation.py tests/smoke/test_wake_strategy_quickstart.py -q` passed (16 tests).
- **Full Phase 11 validation sweep**:
  `python -m pytest tests/unit/test_provider_resolver.py tests/unit/test_assistant_runtime.py tests/unit/test_runtime_contract.py tests/unit/test_release_latency_baselines.py tests/unit/test_settings_provider_persistence.py tests/unit/test_settings_critical_prompt_catalog.py tests/unit/test_provider_registry.py tests/unit/test_wake_strategy_runtime.py tests/unit/test_wake_word_canonical.py -q` passed (65 tests).
  `python -m pytest tests/integration/test_runtime_modes.py tests/integration/test_wearable_startup_readiness.py tests/integration/test_gui_runtime_bridge.py tests/integration/test_runtime_prompt_localization.py tests/integration/test_runtime_offline_behavior.py tests/integration/test_release_latency_pipeline.py tests/integration/test_release_journey_validation.py tests/integration/test_wake_strategy_modes.py -q` passed (30 tests).
  `python -m pytest tests/smoke/test_wake_strategy_quickstart.py tests/smoke/test_runtime_quickstart.py tests/smoke/test_wearable_readiness_quickstart.py -q` passed (20 tests).
  `python -m compileall core tests` passed.
