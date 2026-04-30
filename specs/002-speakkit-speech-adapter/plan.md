# Implementation Plan: Speech Abstraction and SpeakKit Adapter

**Branch**: `[002-speakkit-speech-adapter]` | **Date**: 2026-04-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-speakkit-speech-adapter/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Keep it
aligned with `.specify/memory/constitution.md`.

## Summary

Introduce a replaceable speech-provider layer that supports both legacy speech
components and SpeakKit adapters while preserving current assistant behavior.
Provider selection is persisted, runtime switching is restart-only, and failure
handling follows clarified safety rules: SpeakKit may fallback to legacy,
legacy never auto-switches to SpeakKit, startup unavailability degrades
temporarily to legacy without overwriting the saved provider, and dual-provider
failure transitions to offline with manual restart required.

## Technical Context

**Language/Version**: Python 3.12.4  
**Primary Dependencies**: SpeechRecognition, rapidfuzz, edge-tts, playsound, customtkinter, SpeakKit SDK integration (new adapter target)  
**Storage**: Local JSON profile at `settings/user_profile.json` with persisted speech-provider selection and existing runtime settings  
**Testing**: pytest unit/integration/smoke coverage for provider selection and fallback rules, plus deterministic scripted validation and compile checks when tooling is constrained  
**Target Platform**: Windows desktop debug app and `main.py --console` headless runtime path aligned with future smart-glasses non-visual operation  
**Project Type**: Python voice assistant with shared runtime and pluggable speech adapters  
**Performance Goals**: Maintain >=9/10 parity across legacy and SpeakKit flows, complete recoverable SpeakKit->legacy fallback within 5 seconds, and emit degraded-mode startup notification in 100% of unavailable-provider cases  
**Constraints**: Incremental migration only, no UI-owned runtime logic, restart-only provider switch application, one-way fallback SpeakKit->legacy, preserved persisted provider during startup degradation, offline transition when both providers are unavailable  
**Scale/Scope**: `core/assistant_runtime.py`, new `core/speech/` adapter package, `settings/settings_manager.py`, `settings/profile_store.py`, `core/stt.py`, `core/wake_word.py`, `tts/tts_engine.py`, observer payload alignment in `main.py` and `ui/`, and tests/docs updates under `tests/` and `specs/002-...`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check

- [x] Incremental change: extends current runtime and settings architecture with
      adapter modules rather than replacing layers.
- [x] Runtime/UI separation: keeps provider orchestration in core runtime and
      settings layers; UI remains observer-only.
- [x] Interface boundaries: introduces explicit speech-provider boundaries with
      startup health checks, timeout/failure behavior, and fallback rules.
- [x] Structured results: capability result schema is unchanged in this phase;
      this work formalizes runtime/provider contracts without regressing
      `spoken_text/status/payload/error_code` expectations in downstream layers.
- [x] Quality gates: includes tests, structured provider/runtime logging, smoke
      validation paths, and measurable reliability criteria.

### Post-Design Re-Check

- [x] Design artifacts define provider interfaces and resolver/fallback rules
      without coupling runtime ownership to `ui/`.
- [x] Data model covers persisted provider selection, startup resolution, and
      fallback activation traces needed for safe operation.
- [x] Contracts specify adapter expectations, directional fallback behavior, and
      observer-facing degraded-mode signaling.
- [x] Quickstart validates legacy/SpeakKit parity, restart-only switching,
      startup degradation semantics, and dual-failure offline behavior.
- [x] No constitution violations require Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/002-speakkit-speech-adapter/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- speech-provider-runtime.md
`-- tasks.md
```

### Source Code (repository root)

```text
main.py
core/
|-- assistant_runtime.py
|-- stt.py
|-- wake_word.py
|-- speech/
|   |-- interfaces.py
|   |-- provider_registry.py
|   |-- provider_resolver.py
|   |-- legacy_stt.py
|   |-- legacy_tts.py
|   |-- legacy_wake.py
|   |-- speakkit_stt.py
|   |-- speakkit_tts.py
|   `-- speakkit_wake.py
settings/
|-- settings_manager.py
`-- profile_store.py
tts/
`-- tts_engine.py
ui/
|-- assistant_worker.py
`-- gui_app.py
tests/
|-- unit/
|-- integration/
`-- smoke/
docs/
```

**Structure Decision**: Keep the current repository layout and add a focused
`core/speech/` package for provider interfaces/adapters and selection logic.
Persist provider mode via existing settings/profile flow and integrate with the
shared runtime service instead of introducing a new top-level architecture.

## Complexity Tracking

No constitution violations are expected for this feature. The plan stays within
existing architecture boundaries while introducing explicit adapter contracts
and safe fallback behavior.
