# Quickstart: Speech Abstraction and SpeakKit Adapter

## Goal

Validate that the assistant can run with a replaceable speech pipeline using
legacy and SpeakKit providers while enforcing safe fallback and degradation
rules.

## Prerequisites

1. Create and activate the project virtual environment.
2. Install dependencies from `requirements.txt` and SpeakKit SDK dependency
   chosen for this feature.
3. Ensure microphone and speaker access are available for manual runs.
4. Ensure provider selection can be configured in user profile/settings.

## Validation Matrix

| Scenario | Expected Result |
|---|---|
| Persisted provider `legacy` and available | Runtime uses legacy path |
| Persisted provider `speakkit` and available | Runtime uses SpeakKit path |
| Persisted provider `speakkit` unavailable at startup | Runtime uses legacy for session, notifies degraded mode, keeps persisted provider unchanged |
| Active SpeakKit recoverable failure | Runtime falls back to legacy |
| Active legacy recoverable failure | Runtime does not auto-switch to SpeakKit |
| Both providers unavailable | Runtime transitions to `offline` and requires manual restart |

## Path 1: Legacy Baseline Validation

1. Set persisted provider to `legacy`.
2. Run `python main.py --console` and execute representative wake + command
   flow.
3. Run `python main.py` and verify equivalent behavior in GUI observer path.
4. Confirm parity with existing user-visible behavior.

## Path 2: SpeakKit Provider Validation

1. Set persisted provider to `speakkit`.
2. Run console and GUI flows with same representative commands.
3. Confirm wake, recognition, and spoken response complete successfully.
4. Confirm provider context is visible in runtime config/log events.

## Path 3: Restart-Only Provider Switching

1. Start runtime with one provider active.
2. Request switch to other provider while runtime is active.
3. Confirm request is deferred and current session provider remains unchanged.
4. Restart runtime and confirm deferred provider selection is now active.

## Path 4: Startup Degradation with Unavailable Persisted Provider

1. Persist `speakkit` as provider.
2. Simulate SpeakKit unavailable state at startup.
3. Start runtime and verify:
   - session uses legacy provider
   - degraded-mode notification is emitted
   - persisted provider remains `speakkit`

## Path 5: Fallback Direction and Offline Safety

1. In active SpeakKit mode, trigger recoverable provider failure and confirm
   fallback to legacy.
2. In active legacy mode, trigger recoverable provider failure and confirm no
   auto-switch to SpeakKit.
3. Trigger dual-provider unavailability and confirm offline transition requiring
   manual restart.

## Measurement Targets

| Check | Threshold |
|---|---|
| Legacy/SpeakKit parity across representative flows | >= 9/10 per mode |
| Recoverable fallback completion (SpeakKit->legacy) | <= 5.0s |
| Startup degraded-mode notification coverage | 100% |
| Persisted provider preservation on startup degradation | 100% |
| Legacy no-auto-switch rule compliance | 100% |
| Dual-provider failure offline transition | 100% |

## Suggested Validation Commands

- `python -m compileall main.py core settings tts ui tests`
- `python -m pytest tests/unit -q`
- `python -m pytest tests/integration -q`
- `python -m pytest tests/smoke -q`

If `pytest` is unavailable in the environment, run deterministic scripted
smoke checks and record outcomes in implementation notes until full test tooling
is installed.

## Validation Results (2026-04-17)

| Command | Result |
|---|---|
| `python -m compileall main.py core settings tts ui tests` | PASS |
| `python -m pytest tests/unit -q` | PASS (42 passed) |
| `python -m pytest tests/integration -q` | PASS (19 passed) |
| `python -m pytest tests/smoke -q` | PASS (16 passed) |
| `python -m pytest tests -q` | PASS (77 passed total) |

Notes:
- `pytest` was installed into `venv` to execute the validation sweep.
- Two upstream deprecation warnings from `speech_recognition` were observed
  (`aifc` and `audioop`), with no functional test failures.
