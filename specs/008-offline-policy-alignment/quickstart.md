# Quickstart: Offline Truth and Network Policy Alignment

## Goal

Validate that provider metadata, connectivity probing, startup guidance, and
command-level offline policy all tell the same truth in Arabic and English,
without leaking stale override state across restarts.

## Preconditions

1. Use the project virtual environment and repository root.
2. Keep test coverage deterministic by injecting probe results in unit and
   integration tests instead of requiring real internet access.
3. Exercise both configured speech providers and at least one allowlisted and
   one non-allowlisted capability.

## Validation Paths

### 1. Provider Truth and Startup Reset

1. Simulate a prior session that ended with a manual network override enabled.
2. Start a new runtime session and verify the override resets to `auto`.
3. Run startup with `legacy` and `speakkit` marked as network-required while
   effective connectivity is unavailable.
4. Confirm startup state is `degraded` or `offline`, never `ready`, and the
   spoken guidance uses approved critical prompt surfaces.

Expected outcome:
- Startup readiness, provider metadata, and spoken guidance all agree.
- No prior development override silently survives restart.

### 2. Command Offline Policy Matrix

| Scenario | Expected Decision |
|---|---|
| Network-required capability, offline, not allowlisted | `safe_refusal` |
| Network-required capability, offline, allowlisted | `on_device_fallback` |
| Network-optional capability, offline | `allow_execution` |
| `force_offline` override in development | Offline-safe decision with visible override metadata |
| `force_online` override in development with provider unavailable | No false `ready`; diagnostics still show provider unavailability |

Expected outcome:
- Every decision includes provider id, override mode, effective network
  availability, provider availability, and the final decision reason.

### 3. Probe Uncertainty Handling

1. Feed an `online -> uncertain -> offline` probe sequence.
2. Verify the runtime briefly preserves the last confirmed state during the
   bounded grace window.
3. Confirm the assistant converges to offline-safe behavior when certainty is
   not restored before the deadline.
4. Feed an `offline -> uncertain -> online` sequence and confirm the same logic
   works in the opposite direction.

Expected outcome:
- Short-lived uncertainty does not cause rapid state flapping.
- The assistant does not remain online beyond the approved grace window.

### 4. Suggested Validation Commands

- `python -m pytest tests/unit/test_provider_registry.py tests/unit/test_provider_resolver.py tests/unit/test_connectivity_state_policy.py -q`
- `python -m pytest tests/integration/test_runtime_offline_behavior.py tests/integration/test_runtime_offline_policy_matrix.py tests/integration/test_provider_failure_paths.py -q`
- `python -m pytest tests/smoke/test_speech_provider_quickstart.py tests/smoke/test_offline_truth_quickstart.py -q`
- `python -m compileall core settings tests`

## Operator Notes

- Keep provider network truth aligned with real STT/TTS dependency, not just
  wake-service reachability.
- Treat detected connectivity, effective connectivity, and provider
  availability as separate diagnostic fields.
- Any offline or degraded spoken guidance should continue to resolve through
  the approved critical prompt catalog introduced in Phase 7.

## Validation Evidence (2026-04-20)

- SC-001:
  `python -m pytest tests/integration/test_runtime_offline_behavior.py tests/integration/test_runtime_offline_policy_matrix.py tests/smoke/test_offline_truth_quickstart.py -q`
  -> PASS (`9 passed`)
- SC-002 / SC-004 / SC-007:
  `python -m pytest tests/unit/test_provider_registry.py tests/unit/test_settings_provider_persistence.py tests/integration/test_provider_failure_paths.py tests/integration/test_wearable_startup_readiness.py tests/smoke/test_speech_provider_quickstart.py -q`
  -> PASS (`22 passed`)
- SC-003 / SC-005 / SC-006:
  `python -m pytest tests/unit/test_connectivity_state_policy.py tests/unit/test_provider_resolver.py tests/integration/test_runtime_offline_policy_matrix.py tests/smoke/test_offline_truth_quickstart.py -q`
  -> PASS (`25 passed`)
- Full sweep:
  `python -m pytest tests/unit/test_provider_registry.py tests/unit/test_provider_resolver.py tests/unit/test_settings_provider_persistence.py tests/unit/test_offline_allowlist_policy.py tests/unit/test_connectivity_state_policy.py -q`
  -> PASS (`31 passed`)
- Full sweep:
  `python -m pytest tests/integration/test_runtime_offline_behavior.py tests/integration/test_provider_failure_paths.py tests/integration/test_wearable_startup_readiness.py tests/integration/test_runtime_offline_policy_matrix.py -q`
  -> PASS (`12 passed`)
- Full sweep:
  `python -m pytest tests/smoke/test_speech_provider_quickstart.py tests/smoke/test_offline_truth_quickstart.py -q`
  -> PASS (`9 passed`)
- Full sweep:
  `python -m compileall core settings tests`
  -> PASS
