# Quickstart: Capability Refactor

## Goal

Validate the Phase 4 capability refactor by proving that obstacle detection
works as the first migrated real capability, unmigrated capabilities still use
explicit fallback scaffolding, and timeout or failure handling keeps the shared
runtime responsive.

## Prerequisites

1. Create and activate the project virtual environment.
2. Install dependencies from `requirements.txt`.
3. Ensure microphone and speaker access are available for manual console or GUI
   runs.
4. Prepare an obstacle adapter test double or the chosen local obstacle backend
   for deterministic validation.
5. Keep the current settings profile available so existing language, speech,
   and provider behavior can be compared against baseline timing.

## Validation Matrix

| Scenario | Expected Result |
|---|---|
| Migrated obstacle capability succeeds in console mode | Structured success result, brief spoken output, no fallback |
| Migrated obstacle capability succeeds in GUI mode | Same result shape and user-visible behavior as console mode |
| Migrated obstacle capability backend unavailable | Safe explicit unavailable or failure result, no fallback |
| Migrated obstacle capability times out | `timeout` result within configured timeout and never later than 10.0s |
| Unmigrated OCR, money, face, or emotion capability is invoked | Explicit fallback path remains available with structured result |
| Repeated obstacle start or stop requests | Idempotent result shape with no duplicate side effects |
| System status request after capability changes | Runtime remains responsive and status payload remains machine-readable |

## Path 1: Contract and Registry Validation

1. Run unit tests for capability contracts, registry lookup, timeout runner,
   and obstacle controller behavior.
2. Confirm every handler path returns machine-readable results with
   `spoken_text`, `status`, `payload`, and `error_code` as required.
3. Confirm migrated obstacle capability metadata shows `fallback_policy:
   disabled`.
4. Confirm unmigrated capability registry entries still declare explicit
   fallback mode.

## Path 2: Obstacle Capability End-to-End

1. Start the assistant in console mode with the obstacle adapter available.
2. Issue the existing obstacle enable command and verify a structured success
   result plus clear spoken guidance.
3. Request obstacle status and confirm machine-readable obstacle details are
   returned.
4. Repeat the same flow in GUI mode and confirm equivalent results and spoken
   output.

## Path 3: Timeout and Failure Safety

1. Simulate an obstacle adapter timeout.
2. Confirm runtime receives a `timeout` result with `error_code:
   capability_timeout`.
3. Confirm the runtime emits recovery signaling and remains responsive for the
   next request.
4. Simulate a dependency-unavailable condition and confirm the result is safe,
   explicit, and does not invoke fallback.

## Path 4: Unmigrated Fallback Validation

1. Invoke OCR, money detection, face recognition, and emotion recognition
   through their existing commands.
2. Confirm these capabilities continue to work through explicit fallback
   handlers or registry entries until they are migrated.
3. Confirm result payloads indicate fallback usage clearly when applicable.

## Path 5: Baseline and Regression Timing Capture

1. Capture baseline timings for wake detection, STT turnaround, and TTS start
   before the capability refactor changes are enabled.
2. Capture obstacle `start`, `stop`, and `status` duration on the migrated
   path.
3. Capture runtime recovery timing after a capability timeout or failure.
4. Compare medians to the pre-change baseline and record any regression above
   the allowed threshold.

## Measurement Targets

| Check | Threshold |
|---|---|
| Wake median timing regression | <= 10% above captured baseline |
| STT median timing regression | <= 10% above captured baseline |
| TTS start median timing regression | <= 10% above captured baseline |
| Obstacle `start`, `stop`, or `status` on available backend | <= 3.0s target and always <= configured timeout |
| Any capability action timeout bound | <= 10.0s hard maximum |
| Recovery signaling after timeout or failure | <= 2.0s from detected failure |
| GUI and console parity for migrated obstacle flows | 100% structured-result equivalence |

## Suggested Validation Commands

- `python -m compileall main.py controllers core settings tts ui tests`
- `python -m pytest tests/unit -q`
- `python -m pytest tests/integration -q`
- `python -m pytest tests/smoke -q`

If some tests are not yet present during early implementation slices, execute
the available subset plus deterministic manual obstacle and fallback checks and
record the gap in implementation notes before task completion.

## Validation Results (2026-04-18)

| Command | Result |
|---|---|
| `python -m pytest tests -q` (with `PYTHONPATH=.codex_deps`) | PASS (120 passed) |
| `python -m compileall main.py controllers core settings tts ui tests` | PASS |

### Success Criteria Snapshot

| Criterion | Evidence | Status |
|---|---|---|
| `SC-001` | Obstacle migrated path validated in unit/integration/smoke (`test_obstacle_controller.py`, `test_capability_runtime.py`, `test_capability_refactor_quickstart.py`) | PASS |
| `SC-002` | Contract consistency validated in `test_capability_contracts.py` and `test_capability_registry.py` | PASS |
| `SC-003` | Timeout/failure safety validated in `test_obstacle_controller.py` and `test_capability_refactor_quickstart.py` | PASS |
| `SC-004` | GUI/console parity validated in `test_capability_runtime.py` | PASS |

### Baseline Snapshot (Deterministic Local Test Path)

| Metric | Observed |
|---|---|
| Wake median | `0.000 ms` |
| STT median | `0.000 ms` |
| TTS start median | `0.000 ms` |
| Dispatch median (`start obstacle detection`) | `0.888 ms` |
| Recovery latency after simulated obstacle failure | `1.952 ms` |

Notes:
- Baseline values above were captured with deterministic local test doubles and
  no physical audio/sensor stack attached.
- Production hardware measurements should be captured separately when physical
  microphone, speaker, and obstacle sensor integrations are available.
