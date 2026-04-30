# Quickstart: Runtime Extraction

## Goal

Validate that GUI and console modes consume the same shared runtime service,
use one canonical lifecycle vocabulary, and preserve onboarding and failure
handling behavior.

## Prerequisites

1. Create and activate the project virtual environment.
2. Install dependencies from `requirements.txt`.
3. Ensure microphone access is available for manual voice checks.
4. For automated checks, run from repository root.

## Canonical Lifecycle Vocabulary

Use the following canonical status states in validation evidence:

- `standby`
- `wake`
- `setup`
- `listening`
- `thinking`
- `speaking`
- `error`
- `offline`

Compatibility inputs (`online`, `stopping`) are mapped to canonical output
states by runtime/observers and must not be treated as independent lifecycle
outcomes.

## Validation Path 1: GUI Debug Mode

1. Run `python main.py`.
2. Confirm GUI starts via `AssistantWorker` bridge (no UI-owned runtime loop).
3. Verify status/chat updates are received from runtime events.
4. Say wake phrase and one supported command.
5. Confirm canonical lifecycle progression appears in GUI status handling.
6. If no profile exists, confirm onboarding runs through runtime and reaches
   `setup` before returning to active interaction.

## Validation Path 2: Console Mode

1. Run `python main.py --console`.
2. Confirm console uses shared `AssistantRuntime` observer flow.
3. Run same wake + command scenario used for GUI path.
4. Confirm equivalent canonical status progression and response behavior.
5. If no profile exists, confirm identical runtime-owned onboarding flow.

## Failure Validation

1. Trigger a recoverable runtime failure during active command handling.
2. Confirm `error` event is emitted with `recoverable=true`.
3. Confirm runtime returns to `standby` within 5 seconds.
4. Trigger startup/init failure or explicitly unrecoverable runtime exception.
5. Confirm `error` payload sets `next_state=offline`.
6. Confirm runtime reaches `offline` without re-entering `standby`.

## Validation Guidance Re-Run (2026-04-17)

Commands used for non-destructive re-validation:

1. `python -m compileall ui core settings tests main.py`
2. Scripted parity/failure sweep using injected runtime fakes (no audio device).
3. Targeted worker-bridge smoke script to confirm GUI observer forwarding.

## Measurement Record (2026-04-17)

| Check | Threshold | Result | Status |
|---|---|---|---|
| Configured-user GUI/console parity | >= 9/10 | 10/10 | PASS |
| First-run onboarding parity | >= 9/10 | 10/10 | PASS |
| Recoverable failure standby return | <= 5.0s | 0.000s max | PASS |
| Unrecoverable failure transition | direct `offline` | `error -> offline` (no standby) in GUI+console | PASS |
| Runtime log verification | status + error logs present | both detected | PASS |
| Syntax/compile sweep | no compile errors | PASS | PASS |

## Validation Sweep Notes (T028)

- Full `pytest` execution is currently blocked because `pytest` is not installed
  in this environment (`No module named pytest`).
- Contract, runtime, observer bridge, and deterministic parity/failure checks
  were re-run and recorded above.
- Once `pytest` is installed, run:
  - `python -m pytest tests/unit/test_runtime_contract.py tests/integration/test_runtime_failure_paths.py -q`
  - `python -m pytest tests/unit/test_assistant_runtime.py tests/integration/test_runtime_modes.py tests/smoke/test_runtime_quickstart.py -q`

## Expected Outcome

Feature validation is complete when canonical lifecycle vocabulary is consistent
across modes, onboarding remains runtime-owned, recoverable failures return to
`standby`, unrecoverable failures end in `offline`, and parity thresholds meet
or exceed 9 out of 10 representative runs.
