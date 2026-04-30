# Implementation Plan: Field Diagnostics and Release Consistency

**Branch**: `[012-field-diagnostics-release]` | **Date**: 2026-04-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/012-field-diagnostics-release/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Keep it
aligned with `.specify/memory/constitution.md`.

## Summary

Make release validation reproducible inside the active project interpreter and
make pilot debugging practical by extending the existing release artifact flow
with explicit execution context, expected artifact references, and a canonical
field-safe diagnostic event shape for provider selection, offline-policy, and
interrupt outcomes, then document a short artifact-first troubleshooting path
for maintainers and pilot operators.

## Technical Context

**Language/Version**: Python 3.12.4  
**Primary Dependencies**: Existing runtime stack (`SpeechRecognition`,
`rapidfuzz`, `edge-tts`, `playsound`, `pytest`, `ruff`) plus the current
release-validation models and artifact helpers in `core/release_gates.py`,
`core/release_models.py`, `core/release_artifacts.py`, and runtime execution
surfaces that already produce provider, offline, and interrupt outcomes  
**Storage**: Repository-hosted release artifacts under `artifacts/<run-id>/`,
release documentation under `docs/release/`, and existing in-memory runtime
events; no new persisted datastore  
**Testing**: `pytest` unit, integration, and smoke coverage for
interpreter-pinned release validation, artifact completeness on failed runs,
canonical runtime diagnostics, headless and GUI parity, plus `python -m
compileall` and `ruff check .` in the release-validation path  
**Target Platform**: Windows desktop debug runtime and headless console mode
used as the wearable-reference execution path  
**Project Type**: Python voice assistant with runtime-first orchestration,
structured release validation, and repository-hosted operator guidance  
**Performance Goals**: 100% of release runs record their execution context and
produce summary plus per-gate results plus a diagnostic artifact index even on
failure, at least 19 of 20 comparable reruns in the same environment keep the
same pass or fail decision and expected artifact categories, and a reviewer
who did not create the run can identify the first relevant artifact and likely
failure class within 5 minutes for 5 of 5 representative review bundles  
**Constraints**: Preserve the current layered architecture; keep diagnostic
meaning runtime-owned rather than GUI-owned; execute validation via the active
Python interpreter instead of PATH-dependent tools; keep default field
artifacts free of raw user utterances; keep provider, offline-policy, and
interrupt diagnostics comparable across headless and GUI entry paths; reuse the
existing release artifact and troubleshooting surfaces instead of building a
new observability subsystem  
**Scale/Scope**: Extend release run context and artifact reporting in
`scripts/release_validate.py`, `core/release_gates.py`,
`core/release_models.py`, and `core/release_artifacts.py`; standardize runtime
diagnostic envelopes in the provider-selection, offline-policy, and interrupt
boundaries under `core/`; update `docs/release/troubleshooting.md`; and add
Phase 12 validation across `tests/unit/`, `tests/integration/`, and
`tests/smoke/`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check

- [x] Incremental change: the plan extends the existing release, runtime, and
      documentation paths without introducing a top-level rewrite or parallel
      validation stack.
- [x] Runtime/UI separation: diagnostic meaning remains owned by shared runtime
      and release boundaries, not by `ui/`-specific logging or display code.
- [x] Interface boundaries: release results and runtime diagnostic events are
      defined through explicit contracts so provider, offline-policy, and
      interrupt surfaces stay replaceable and testable.
- [x] Safety and accessibility: the design preserves truthful degraded and
      refusal outcomes, supports non-visual/headless investigation, and keeps
      field evidence privacy-aware by excluding raw utterances by default.
- [x] Quality gates: the plan includes structured artifacts, unit/integration
      and smoke validation, and reproducibility checks for the active
      interpreter environment.

### Post-Design Re-Check

- [x] Phase 0 research resolves interpreter pinning, artifact completeness,
      field-safe diagnostic shape, and troubleshooting ordering without leaving
      blocking ambiguities.
- [x] Data model defines the release validation context, release validation
      outcome, runtime diagnostic event, and troubleshooting workflow step.
- [x] Contracts define machine-readable release-result and runtime-diagnostic
      payloads plus the review workflow structure operators follow.
- [x] Quickstart defines repeatable validation for reproducible release runs,
      failed-run artifact evidence, structured diagnostics, and headless/GUI
      consistency.
- [x] No constitution violations require Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/012-field-diagnostics-release/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- pilot-troubleshooting-workflow-contract.md
|   |-- release-validation-result-contract.md
|   `-- runtime-diagnostic-event-contract.md
`-- tasks.md
```

### Source Code (repository root)

```text
main.py
controllers/
core/
settings/
tts/
ui/
tests/
docs/
scripts/
artifacts/
```

**Structure Decision**: Keep Phase 12 within the current repository layout.
`scripts/release_validate.py` remains the entrypoint for release execution,
`core/release_*` remains the authority for run models and artifact persistence,
runtime diagnostic production stays in shared `core/` flows rather than GUI
code, and operator guidance remains in `docs/release/`. Any helper added for
canonical diagnostics should be a small `core/` module rather than a new
top-level package.

## Complexity Tracking

No constitution violations are expected for this feature. The design remains
incremental, runtime-first, adapter-oriented, safety-aware, and measurable
through the current release-validation and troubleshooting surfaces.
