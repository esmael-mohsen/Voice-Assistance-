# Implementation Plan: Runtime Extraction

**Branch**: `[001-runtime-extraction]` | **Date**: 2026-04-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-runtime-extraction/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Keep it
aligned with `.specify/memory/constitution.md`.

## Summary

Extract the assistant runtime loop and first-run voice onboarding from
`ui/assistant_worker.py` into a reusable `core/assistant_runtime.py` service
while preserving the current end-user behavior. GUI debug mode and console mode
will both consume the same runtime lifecycle and event contract, and this phase
will avoid speech abstraction, parser redesign, or command-result refactoring
except where minimal routing work is required for parity, safety, or stability.

## Technical Context

**Language/Version**: Python 3.12.4  
**Primary Dependencies**: SpeechRecognition, rapidfuzz, edge-tts, playsound,
customtkinter  
**Storage**: Local JSON profile at `settings/user_profile.json`  
**Testing**: pytest for new runtime-focused tests plus GUI and console smoke
validation  
**Target Platform**: Windows desktop debug app with `main.py --console` as the
current non-visual path and a shared runtime ready for future smart-glasses
deployment  
**Project Type**: Python voice assistant with shared runtime service and debug
GUI  
**Performance Goals**: Preserve current wake-and-command responsiveness, return
recoverable failures to `standby` within 5 seconds, and achieve equivalent
lifecycle behavior in at least 9 of 10 smoke runs per mode  
**Constraints**: Behavior-preserving phase; first-run onboarding remains in
scope; no speech-provider abstraction; no parser, resolver, or dispatcher
redesign beyond routing changes; non-visual operation must remain usable  
**Scale/Scope**: Primary changes in `main.py`, new `core/assistant_runtime.py`,
`ui/assistant_worker.py`, `ui/gui_app.py`, and new `tests/`; minimal support
changes in `settings/` or `core/` only when required for shared runtime
integration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check

- [x] Incremental change: adds a new runtime service and migrates behavior in
      small slices without rewriting the layered application.
- [x] Runtime/UI separation: moves authoritative runtime flow out of `ui/`
      while preserving the GUI as an observer and debug surface.
- [x] Interface boundaries: Phase 1 defines a runtime service and runtime event
      contract without prematurely introducing speech-provider abstractions.
- [x] Structured results: capability result redesign is out of scope, and this
      plan instead formalizes a shared runtime event contract for observers.
- [x] Quality gates: includes pytest coverage, structured logging expectations,
      and repeatable GUI/console smoke validation.

### Post-Design Re-Check

- [x] Design keeps `core/assistant_runtime.py` as the single shared runtime
      authority consumed by GUI and console observers.
- [x] Contracts document lifecycle events and control boundaries without
      coupling them to `Queue` or `customtkinter`.
- [x] Data model captures runtime session, event, settings snapshot, and
      onboarding state needed for first-run parity.
- [x] Quickstart validates both configured and first-run onboarding paths in
      GUI and console modes.
- [x] No constitution violations require Complexity Tracking for this feature.

## Project Structure

### Documentation (this feature)

```text
specs/001-runtime-extraction/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- runtime-service.md
`-- tasks.md
```

### Source Code (repository root)

```text
main.py
core/
|-- assistant_runtime.py     # new shared runtime service
|-- dispatcher.py
|-- stt.py
|-- wake_word.py
settings/
|-- settings_manager.py
|-- profile_store.py
tts/
|-- tts_engine.py
ui/
|-- assistant_worker.py
|-- gui_app.py
tests/
|-- unit/
|-- integration/
`-- smoke/
docs/
```

**Structure Decision**: Keep the current repository layout and add
`core/assistant_runtime.py` as the shared runtime service. `ui/assistant_worker.py`
becomes a UI bridge, `main.py --console` becomes the current non-visual
observer entry point, and tests are added under `tests/` without introducing a
new top-level package.

## Complexity Tracking

No constitution violations are expected for this feature. The plan stays within
the existing architecture and defers broader speech and command-layer redesign
to later phases.
