# Implementation Plan: Capability Refactor

**Branch**: `[004-capability-refactor]` | **Date**: 2026-04-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-capability-refactor/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Keep it
aligned with `.specify/memory/constitution.md`.

## Summary

Incrementally replace the shared `controllers/mock_controllers.py` bottleneck
with dedicated capability handlers and a registry-backed contract while keeping
the existing bilingual command layer and runtime flows intact. The first slice
delivers obstacle detection as the first migrated real capability behind an
explicit obstacle adapter and per-capability timeout policy, keeps fallback
restricted to unmigrated or test-only capabilities, and adds structured
results, logging, contract tests, and GUI or console parity validation.

## Technical Context

**Language/Version**: Python 3.12.4  
**Primary Dependencies**: Existing `core.assistant_runtime`,
`core.dispatcher`, `core.resolver`, and `core.command_models`; current
`settings.settings_manager`; `pytest` for unit, integration, and smoke
coverage; standard-library concurrency utilities for bounded capability
execution; existing `logging` pipeline for structured runtime and capability
events  
**Storage**: In-memory capability registry, timeout policy metadata, and
runtime capability status snapshots; existing settings JSON remains unchanged
for this phase and no new persisted datastore is required  
**Testing**: `pytest` unit coverage for capability contracts, registry, timeout
runner, and obstacle controller behavior; integration coverage for resolver,
dispatcher, and runtime parity; smoke validation for representative GUI and
console flows; `python -m compileall` for import safety; documented baseline
capture for wake, STT, TTS, capability execution, and recovery timing  
**Target Platform**: Windows desktop via `python main.py` plus console or
headless runtime via `python main.py --console`, with the headless runtime kept
as the reference path for future wearable use  
**Project Type**: Python voice assistant with a shared runtime, bilingual
command layer, and incrementally extracted capability-controller architecture  
**Performance Goals**: Capture current baseline timings for wake detection, STT
turnaround, TTS start, obstacle capability execution, and recovery from
capability failure; keep wake, STT, and TTS median timings within 10% of the
captured baseline; keep obstacle `start`, `stop`, and `status` actions within
their configured timeout windows with a hard maximum of 10.0 seconds and a
planned target of 3.0 seconds or less for the obstacle path on an available
backend; return a safe failure outcome and emit recovery signaling within 2.0
seconds after a detected capability timeout or dependency failure  
**Constraints**: Do not add new user-facing commands; preserve runtime or UI
separation by keeping capability orchestration in `core/` and controllers in
`controllers/`; fallback is allowed only for unmigrated or explicit test-only
capabilities; migrated real capabilities must safe-fail instead of silently
reverting to mocks; maintain equivalent GUI and console outcomes; keep spoken
responses brief and non-visual-first; declare weak-network or unavailable-
dependency behavior at the capability boundary even when the first capability
is local-sensor-first  
**Scale/Scope**: `controllers/mock_controllers.py`, new capability contract and
registry modules under `controllers/`, the first real
`controllers/obstacle_controller.py`, resolver and dispatcher routing updates
in `core/resolver.py` and `core/dispatcher.py`, runtime normalization and
logging in `core/assistant_runtime.py`, and new unit, integration, and smoke
coverage under `tests/`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check

- [x] Incremental change: the plan keeps the current repository layout and
      replaces the shared mock bottleneck in small slices, starting with a
      registry and one migrated capability instead of a rewrite.
- [x] Runtime/UI separation: capability orchestration remains in
      `core/resolver.py`, `core/dispatcher.py`, and `core/assistant_runtime.py`;
      `ui/` stays a debug observer only.
- [x] Interface boundaries: the first real capability is introduced behind an
      explicit obstacle adapter and all capability handlers conform to a shared
      contract with timeout and fallback rules.
- [x] Structured results: the design defines how `spoken_text`, `status`,
      `payload`, and `error_code` are produced for capability execution and
      status snapshots without using spoken strings as machine state.
- [x] Quality gates: unit, integration, and smoke tests, structured logging,
      and latency or reliability baselines are part of the plan.

### Post-Design Re-Check

- [x] Research formalizes a registry-backed capability contract, a shared
      timeout runner, explicit migrated-versus-fallback rules, and the first
      real obstacle adapter boundary.
- [x] Data model covers capability descriptors, action bindings, requests,
      results, status snapshots, timeout policies, and obstacle observations.
- [x] Contracts define the runtime-facing capability surface and the obstacle
      adapter boundary clearly enough for resolver, runtime, and tests to use
      consistently.
- [x] Quickstart exercises obstacle end-to-end validation, timeout recovery,
      unmigrated fallback behavior, and GUI or console parity with measurable
      checks.
- [x] No constitution violations require entries in `Complexity Tracking`.

## Project Structure

### Documentation (this feature)

```text
specs/004-capability-refactor/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- capability-runtime.md
|   `-- obstacle-sensor-adapter.md
`-- tasks.md
```

### Source Code (repository root)

```text
main.py
controllers/
|-- capability_contracts.py
|-- capability_registry.py
|-- mock_controllers.py
`-- obstacle_controller.py
core/
|-- assistant_runtime.py
|-- command_models.py
|-- dispatcher.py
`-- resolver.py
settings/
tts/
ui/
tests/
|-- integration/
|   `-- test_capability_runtime.py
|-- smoke/
|   `-- test_capability_refactor_quickstart.py
`-- unit/
    |-- test_capability_contracts.py
    |-- test_capability_registry.py
    `-- test_obstacle_controller.py
docs/
```

**Structure Decision**: Keep the existing repository layout and introduce the
capability refactor as a thin layer inside `controllers/` plus routing updates
in `core/`. Deliver obstacle detection first as a dedicated controller module
backed by an explicit adapter boundary, and keep unmigrated capabilities behind
explicit fallback registry entries instead of continuing to expand the shared
mock module as the main runtime dependency.

## Complexity Tracking

No constitution violations are expected for this feature. The design keeps the
current layered runtime intact, introduces explicit capability boundaries in
place, and avoids a broader controller or runtime rewrite.
