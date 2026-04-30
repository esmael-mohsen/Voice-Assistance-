# STT Rollout Observability Validation Record

## Run Metadata

- Date: 2026-04-28
- Feature: `021-stt-rollout-observability`
- Branch: `023-stt-rollout-observability`
- Executor: `venv\Scripts\python.exe`

## Unit Test Validation (T049)

Command:

```powershell
venv\Scripts\python.exe -m pytest tests\unit\test_runtime_diagnostics.py tests\unit\test_stt_observability_contract.py tests\unit\test_stt_rollout_modes.py tests\unit\test_stt_failure_scenario_contract.py tests\unit\test_pocketsphinx_decommission_contract.py tests\unit\test_release_gate_models.py -q
```

Result:

- `21 passed`
- Deprecation warnings from `speech_recognition` (`aifc`, `audioop`) only.

## Integration and Smoke Validation (T050)

Integration command:

```powershell
venv\Scripts\python.exe -m pytest tests\integration\test_stt_observability_pipeline.py tests\integration\test_stt_rollout_release_gates.py tests\integration\test_stt_failure_scenario_recovery.py tests\integration\test_pocketsphinx_decommission.py tests\integration\test_pi_qualification_release_gates.py tests\integration\test_release_gate_pipeline.py -q
```

Integration result:

- `12 passed`
- Deprecation warnings from `speech_recognition` (`aifc`, `audioop`) only.

Smoke command:

```powershell
venv\Scripts\python.exe -m pytest tests\smoke\test_stt_rollout_observability_quickstart.py -q
```

Smoke result:

- `1 passed`
- Deprecation warnings from `speech_recognition` (`aifc`, `audioop`) only.

## Compile and Lint Validation (T051)

Commands:

```powershell
venv\Scripts\python.exe -m compileall core tests scripts
venv\Scripts\python.exe -m ruff check .
```

Results:

- `compileall` completed successfully for `core`, `tests`, and `scripts`.
- `ruff check` reported: `All checks passed!`

## Additional Runtime Regression Guard

Command:

```powershell
venv\Scripts\python.exe -m pytest tests\unit\test_assistant_runtime.py tests\unit\test_stt_feature_flags.py -q
```

Result:

- `39 passed`
- Deprecation warnings from `speech_recognition` (`aifc`, `audioop`) only.

## Evidence Notes

- Field-safe STT fixtures were added under
  `tests/fixtures/stt_rollout_observability/`.
- Phase 21 release validation now supports STT rollout evidence artifacts:
  `stt-events.json`, `stt-rollup.json`, `stt-failure-scenarios.json`,
  `stt-release-gate.json`, `pi4-stt-qualification.json`,
  `pocketsphinx-decommission.json`.
