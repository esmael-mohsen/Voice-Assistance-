# Quickstart: Quality Gates and Release Preparation

## Goal

Validate a pilot release candidate with deterministic quality gates so runtime
regressions, localization corruption, and latency degradations are blocked
before approval.

## Prerequisites

1. Activate the project virtual environment.
2. Install dependencies from `requirements.txt`.
3. Confirm current branch is `006-quality-gates-release`.
4. Ensure microphone/speaker permissions are available for runtime-path tests.
5. Ensure a clean artifacts folder path is available for validation evidence.

## Required Gate Matrix

| Gate | Expected Result |
|---|---|
| Compile validation | Python modules compile without import/syntax errors |
| Unit/integration/smoke tests | All mandatory suites pass |
| Lint validation | No blocking lint errors |
| Lifecycle and primary journey validation | Startup, standby, wake, listening, speaking, error, and offline flows pass |
| Localization regression (AR/EN) | All critical prompts pass integrity checks |
| Baseline comparison | No metric breaches approved per-metric thresholds |
| Release checklist | Offline behavior, emergency controls, audio access, and crash recovery confirmed |

## Path 1: Core Quality Gates

1. Run compile validation.
2. Run `pytest` suites (unit, integration, smoke).
3. Run lint checks.
4. Record gate outputs into a single run artifact bundle.

## Path 2: Lifecycle and Journey Readiness

1. Execute lifecycle-focused integration validation.
2. Execute primary user-journey scenarios.
3. Confirm no unresolved critical failures remain before proceeding.

## Path 3: Localization Regression

1. Run critical prompt validation against Arabic and English prompt catalogs.
2. Confirm no missing, garbled, or mismatched critical prompt output.
3. Fail release gate immediately if any critical prompt check fails.

## Path 4: Baseline Capture and Comparison

1. Capture required timing metrics:
   `wake_to_listen`, `listen_to_result`, `result_to_speech_start`.
2. Compare candidate metrics to latest approved baseline.
3. Enforce per-metric threshold policy and fail on any breach.

## Path 5: Checklist and Override Governance

1. Complete the release checklist with owner + timestamp evidence.
2. If a blocking gate fails and emergency release is required, record override
   request with reason.
3. Require dual approval by Engineering Lead and QA/Safety owner.
4. Set remediation due timestamp within 48 hours and track closure evidence.

## Suggested Validation Commands

- `python -m compileall main.py core settings tts ui tests`
- `python -m pytest tests/unit -q`
- `python -m pytest tests/integration -q`
- `python -m pytest tests/smoke -q`
- `ruff check .`

While Phase 6 automation scripts are being implemented, run the commands above
and store outputs in a release artifact bundle for each candidate.

## Evidence Retention

- Persist run summary, test outputs, localization results, baseline comparison,
  checklist evidence, and override artifacts (if used).
- Retain all required validation artifacts for 180 days from release approval.

## Implementation Evidence (2026-04-19)

### Story Validation Runs

- `python -m pytest tests/integration/test_release_lifecycle_validation.py tests/integration/test_release_journey_validation.py tests/integration/test_release_localization_validation.py -q` -> `6 passed`
- `python -m pytest tests/unit/test_release_latency_baselines.py tests/integration/test_release_latency_pipeline.py -q` -> `4 passed`
- `python -m pytest tests/unit/test_release_quality_gate_blocking.py tests/integration/test_release_workflow.py tests/smoke/test_release_quality_gates_quickstart.py -q` -> `9 passed`

### Full Validation Sweep

- `python -m compileall main.py core settings tts ui tests` -> `success`
- `python -m pytest tests/unit -q` -> `104 passed`
- `python -m pytest tests/integration -q` -> `51 passed`
- `python -m pytest tests/smoke -q` -> `28 passed`
- `%APPDATA%\Python\Python312\Scripts\ruff.exe check .` -> `All checks passed` (using repository Ruff config)
