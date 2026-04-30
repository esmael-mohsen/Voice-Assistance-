# Quickstart: STT Observability, Rollout Gates, and PocketSphinx Decommission

## Purpose

Validate that cloud-primary STT behavior is measurable, field-safe,
rollback-friendly, Pi 4 qualified, and free of default PocketSphinx production
usage.

## Prerequisites

1. Use Python 3.12.4 in the project virtual environment.
2. Keep STT diagnostics field-safe; do not persist raw audio or raw
   utterances during validation.
3. Use local release artifacts as the default evidence destination.
4. Keep rollback controls available for every rollout mode until field
   validation is complete.
5. Treat Raspberry Pi 4 evidence as required for pilot or field approval.

## Rollout Modes

Validate modes in this order:

1. `shadow`: cloud recognition may run for metadata, but user-visible behavior
   remains unchanged.
2. `wake_only`: cloud-primary wake is evaluated while command behavior remains
   on the previous safe path.
3. `commands_low_risk`: cloud-primary command recognition is limited to
   low-risk commands with strict fallback.
4. `full_cloud_primary`: wake and commands use cloud-primary behavior with
   strict local fallback.

Rollback settings or environment controls override any rollout mode when set.

## Validation Steps

### 1. STT Telemetry Events And Rollups

1. Exercise cloud success, cloud failure, strict fallback, rescue recognition,
   retry, clipping, timeout, Arabic failure, and language mismatch fixtures.
2. Inspect generated field-safe events and per-run rollups.

Expected result:
- Events include source, rollout mode, status, confidence bucket, failure
  category, recovery outcome, latency bucket, and reason codes.
- Rollups expose cloud failure frequency, fallback frequency, confidence
  distribution, retry rate, clipping rate, timeout rate, Arabic failure count,
  and language mismatch rate.
- No raw audio or raw utterance content is present.

### 2. Rollout And Rollback Controls

1. Validate `shadow`, `wake_only`, `commands_low_risk`, and
   `full_cloud_primary` in order.
2. Repeat with rollback controls enabled.

Expected result:
- `shadow` collects metadata without changing user-visible behavior.
- Later modes only advance when prior mode evidence is available.
- Rollback controls override the requested mode and record the reason.

### 3. Blocking Release Gates

Run release validation with passing and failing evidence for:

- cloud-primary configuration
- strict fallback availability
- default PocketSphinx usage
- wake fallback correctness
- protected-command confirmation
- bilingual command regression
- bounded STT failure recovery
- Raspberry Pi 4 qualification

Expected result:
- Missing or failed safety-critical evidence blocks pilot and field readiness.
- Gate results include field-safe reason codes and evidence references.

### 4. STT Failure Scenario Recovery

Exercise:

- no network
- missing credentials
- expired credentials
- cloud quota or rate errors
- cloud timeout
- missing strict fallback model
- microphone timeout
- repeated clipped utterances
- language mismatch

Expected result:
- Every scenario resolves to fallback, retry, safe refusal, or standby.
- No scenario causes an unhandled runtime crash.
- Spoken recovery remains short and non-visual.

### 5. Raspberry Pi 4 Qualification

1. Run the qualification workflow on Raspberry Pi 4 hardware.
2. Capture wake latency, command recognition latency, fallback latency, CPU
   usage, memory usage, thermal evidence, repeated wake cycles, and telemetry
   completeness.
3. Compare against `settings/release_thresholds.json`.

Expected result:
- Passing evidence is attached for pilot or field approval.
- Missing or failed Pi 4 evidence blocks pilot and field readiness.

### 6. PocketSphinx Decommission

1. Validate default production STT readiness with PocketSphinx installed but
   not explicitly enabled for compatibility.
2. Inspect candidate and invocation evidence plus required accuracy baseline
   membership.
3. Review STT documentation.

Expected result:
- Default candidate count is zero.
- Default invocation count is zero.
- Production accuracy baseline does not require Sphinx-specific tests.
- Documentation describes PocketSphinx as non-primary and compatibility-only.

## Suggested Automated Checks

```powershell
python -m pytest tests/unit/test_stt_observability_contract.py tests/unit/test_stt_rollout_modes.py tests/unit/test_stt_failure_scenario_contract.py tests/unit/test_pocketsphinx_decommission_contract.py -q
python -m pytest tests/integration/test_stt_observability_pipeline.py tests/integration/test_stt_rollout_release_gates.py tests/integration/test_stt_failure_scenario_recovery.py tests/integration/test_pi_qualification_release_gates.py -q
python -m pytest tests/smoke/test_stt_rollout_observability_quickstart.py -q
python -m compileall core tests scripts
python -m ruff check .
```

If a listed test file does not exist during implementation, create it for the
missing scenario rather than dropping the scenario from validation.

## Manual Smoke Check

1. Start the assistant in headless or GUI debug mode with field-safe
   diagnostics enabled.
2. Run one successful cloud attempt, one cloud failure with strict fallback,
   one language mismatch, and one rollback override scenario.
3. Review generated local release evidence.

Expected result:
- User-visible behavior remains bounded and non-visual.
- Diagnostics explain the recognition source, rollout mode, failure category,
  recovery outcome, and release gate readiness without raw content.

## Success Criteria Mapping

- `SC-001`: Telemetry events and rollups cover STT attempts and failure
  categories without raw content.
- `SC-002`: Blocking release gates reject unsafe or incomplete rollout
  evidence.
- `SC-003`: Failure scenarios recover through fallback, retry, safe refusal,
  or standby without crashes.
- `SC-004`: Pi 4 qualification evidence reports recognition latency and
  resource metrics against the approved threshold policy.
- `SC-005`: PocketSphinx has zero default production candidates or
  invocations.
- `SC-006`: Field diagnostics attribute covered recognition failures to the
  correct category.
