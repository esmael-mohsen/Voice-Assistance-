# Implementation Plan: STT Observability, Rollout Gates, and PocketSphinx Decommission

**Branch**: `[023-stt-rollout-observability]` | **Date**: 2026-04-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/021-stt-rollout-observability/spec.md`

**Note**: This plan is produced by `/speckit.plan` and follows
`.specify/memory/constitution.md`.

## Summary

Make the cloud-primary STT architecture measurable, rollout-safe, and ready
for Raspberry Pi 4 field qualification by adding field-safe STT telemetry,
per-run rollups, blocking release gates, bounded failure-scenario recovery,
rollback-aware rollout modes, and final PocketSphinx decommission evidence.

The implementation stays inside existing runtime and release-validation
surfaces. `core/stt.py` and `core/assistant_runtime.py` remain responsible for
recognition outcomes and bounded recovery, `core/runtime_diagnostics.py` and
`core/release_metrics.py` carry field-safe telemetry, `core/release_gates.py`
and `core/release_models.py` express readiness decisions, and docs under
`docs/` explain rollout, troubleshooting, Pi 4 qualification, and
PocketSphinx compatibility status.

## Technical Context

**Language/Version**: Python 3.12.4  
**Primary Dependencies**: Existing runtime stack (`SpeechRecognition`,
`rapidfuzz`, `edge-tts`, `playsound`, `customtkinter`), optional Google Cloud
STT boundary in `core/speech/google_cloud_stt.py`, strict Vosk fallback in
`core/stt.py`, release telemetry helpers in `core/release_metrics.py`,
field-safe diagnostics in `core/runtime_diagnostics.py`, release gate models
and orchestration in `core/release_models.py` and `core/release_gates.py`, and
`pytest`/`ruff` validation  
**Storage**: No new persisted datastore; field-safe STT events, per-run
rollups, release summaries, Pi 4 evidence, and decommission evidence are local
release artifacts with the existing 180-day retention policy; raw audio and
raw utterances are not stored by default  
**Testing**: `pytest` unit coverage for telemetry contracts, rollout mode
resolution, blocking release gates, failure classification, and PocketSphinx
decommission evidence; integration coverage for STT failure paths, release
gate pipeline, Pi 4 qualification, privacy diagnostics, and default
PocketSphinx exclusion; smoke validation for quickstart release readiness;
`python -m compileall core tests` and `python -m ruff check .` remain final
quality gates  
**Target Platform**: Windows desktop debug app and headless console runtime,
with Raspberry Pi 4 as the required pilot and field qualification hardware  
**Project Type**: Python voice assistant with runtime-first speech adapters,
field-safe diagnostics, and local release validation artifacts  
**Performance Goals**: 100% of covered STT fixtures emit event records and
per-run rollups without raw content; 100% of blocking gate regression fixtures
fail release readiness; 100% of covered failure scenarios resolve to fallback,
retry, safe refusal, or standby; Pi 4 qualification reports recognition
latency and resource metrics against the approved threshold policy; production
readiness evidence reports zero default PocketSphinx candidates or invocations  
**Constraints**: No external telemetry service required; no raw audio or raw
utterance retention by default; rollback controls override rollout mode until
field validation completes; release gates block pilot and field approval for
missing cloud config, missing strict fallback, unsafe wake fallback,
protected-command regression, bilingual regression, bounded-recovery
regression, default PocketSphinx usage, and missing or failed Pi 4
qualification; compatibility-only Sphinx checks stay outside the required
production accuracy baseline  
**Scale/Scope**: Expected implementation changes in `core/stt.py`,
`core/assistant_runtime.py`, `core/runtime_diagnostics.py`,
`core/release_metrics.py`, `core/release_models.py`, `core/release_gates.py`,
`scripts/release_validate.py`, `requirements.txt` if active dependencies
change, `settings/release_thresholds.json` if threshold keys need extension,
and documentation under `docs/STTInfo.md`, `docs/release/troubleshooting.md`,
and `docs/release/audio_frontend_qualification.md`; validation lives under
`tests/unit/`, `tests/integration/`, and `tests/smoke/`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check

- [x] Incremental change: the plan extends existing STT runtime,
      diagnostics, metrics, release gate, and documentation surfaces without a
      rewrite or new top-level runtime package.
- [x] Runtime/UI separation: observability, rollout decisions, fallback
      recovery, and release gating remain in `core/`, `scripts/`, `settings/`,
      and docs; `ui/` remains debug-only.
- [x] Interface boundaries: cloud STT, strict Vosk fallback, and
      PocketSphinx compatibility stay behind existing provider and rollout
      boundaries with timeout and fallback behavior.
- [x] Structured results: STT telemetry, failure scenario results, release
      gate outcomes, Pi 4 qualification snapshots, and decommission evidence
      use machine-readable field-safe payloads.
- [x] Quality gates: unit, integration, smoke, privacy, release-gate,
      latency/resource, and decommission validation are planned.

### Post-Design Re-Check

- [x] Phase 0 research resolves telemetry destination, event and rollup shape,
      rollout precedence, blocking gates, failure taxonomy, Pi 4 evidence, and
      PocketSphinx decommission policy.
- [x] Data model defines STT telemetry events, rollups, rollout decisions,
      release gates, failure scenario results, Pi 4 qualification snapshots,
      and PocketSphinx decommission evidence.
- [x] Contracts define the field-safe payloads and readiness decisions that
      runtime code, release validation, and tests must preserve.
- [x] Quickstart defines repeatable validation for observability, rollout
      modes, failure recovery, release gates, Pi 4 qualification, and
      PocketSphinx decommission.
- [x] No constitution violations require Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/021-stt-rollout-observability/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- failure-scenario-result-contract.md
|   |-- pi4-qualification-snapshot-contract.md
|   |-- pocketsphinx-decommission-contract.md
|   |-- release-gate-result-contract.md
|   |-- rollout-mode-contract.md
|   |-- stt-telemetry-event-contract.md
|   `-- stt-telemetry-rollup-contract.md
`-- tasks.md              # generated by /speckit.tasks after this plan
```

### Source Code (repository root)

```text
main.py
core/
|-- assistant_runtime.py
|-- command_models.py
|-- release_gates.py
|-- release_metrics.py
|-- release_models.py
|-- runtime_diagnostics.py
|-- stt.py
|-- speech/
|   |-- google_cloud_stt.py
|   `-- provider_resolver.py
scripts/
|-- release_validate.py
settings/
|-- release_thresholds.json
docs/
|-- STTInfo.md
|-- implementationPlan.md
`-- release/
    |-- audio_frontend_qualification.md
    `-- troubleshooting.md
tests/
|-- unit/
|-- integration/
`-- smoke/
```

**Structure Decision**: Keep Phase 21 inside the existing speech runtime and
release validation pipeline. Add small model/helper extensions only where
needed in `core/release_metrics.py`, `core/runtime_diagnostics.py`,
`core/release_models.py`, `core/release_gates.py`, and `core/stt.py`. No new
top-level telemetry service or persistent datastore is justified.

## Complexity Tracking

No constitution violations are expected. The feature remains incremental,
runtime-first, adapter-aware, field-safe, rollback-friendly, and measurable
through existing local release artifacts and tests.
