# Implementation Plan: Audio Front-End, Hybrid STT, and Command Canonicalization

**Branch**: `[014-audio-stt-canonicalization]` | **Date**: 2026-04-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/014-audio-stt-canonicalization/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Keep it
aligned with `.specify/memory/constitution.md`.

## Summary

Improve command capture quality and recognition reliability by extending the
existing speech stack with profile-driven audio pre-processing, endpoint-aware
capture metadata, a local-first hybrid STT flow with bounded rescue behavior,
and an expanded canonicalization layer that keeps noisy bilingual transcripts
inside the supported command space while preserving safe degraded operation on
Raspberry Pi 4-class hardware.

## Technical Context

**Language/Version**: Python 3.12.4  
**Primary Dependencies**: Existing runtime stack (`SpeechRecognition`,
`pocketsphinx`, `vosk`, `webrtcvad`, `rapidfuzz`, `edge-tts`, `playsound`,
`customtkinter`) plus current runtime modules in `core/stt.py`,
`core/assistant_runtime.py`, `core/command_post_processing.py`,
`core/speech/provider_resolver.py`, `core/speech/provider_registry.py`, and
`settings/settings_manager.py`  
**Storage**: Existing persisted runtime profile in
`settings/user_profile.json` for speech-policy toggles and profile defaults;
curated offline benchmark fixtures and generated validation artifacts under the
repository; no new persistent datastore  
**Testing**: `pytest` unit, integration, and smoke coverage for audio
pre-processing, endpointing, hybrid recognition routing, canonicalization,
closed-vocabulary filtering, and Raspberry Pi qualification evidence;
`python -m compileall` and `ruff check .` remain part of the validation path  
**Target Platform**: Windows desktop debug runtime and headless console mode as
the reference path, with Raspberry Pi 4 Model B as the deployment
qualification target  
**Project Type**: Python voice assistant with runtime-first speech adapters,
bilingual command handling, assistive safety gates, and provider-based
degraded-mode behavior  
**Performance Goals**: At least 90% of representative command captures finish
without suspected clipping; command-resolution success on the maintained noisy
local benchmark improves by at least 20 percentage points over the pre-phase
baseline; closed-vocabulary onboarding and confirmation accuracy reaches at
least 95%; 95% of local-first command interactions begin spoken response
within 2.5 seconds; 95% of rescue-path interactions begin spoken response
within 5 seconds; qualification evidence records the supported profile and any
disabled optional enhancement on every run  
**Constraints**: Preserve the current layered architecture; keep runtime logic
in `core/` and settings policy in `settings/`; keep the speech path free and
local-first by default; respect Raspberry Pi 4 CPU and latency limits; use one
bounded re-listen and one bounded closed-choice retry at most; keep default
telemetry metadata-only; exclude live user audio and raw transcripts from
default evidence; maintain safe headless behavior and existing risky-command
confirmation protections  
**Scale/Scope**: Extend `core/stt.py` and `core/speech/legacy_stt.py` with
capture profiles, endpoint scoring, and hybrid local-first or rescue routing;
add a focused `core/audio/` package for pre-processing and profile utilities;
expand `core/assistant_runtime.py` and `core/command_post_processing.py` for
capture-aware decisions, canonicalization, and closed-vocabulary handling;
thread settings through `settings/settings_manager.py` and
`settings/profile_store.py`; keep provider boundaries centered in
`core/speech/`; add benchmark fixtures and validation coverage under `tests/`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check

- [x] Incremental change: the design extends the current speech and runtime
      pipeline through `core/stt.py`, `core/assistant_runtime.py`, and a small
      `core/audio/` addition instead of replacing the stack.
- [x] Runtime/UI separation: capture policy, hybrid recognition, and
      canonicalization remain runtime-owned in `core/` and `settings/`, not in
      `ui/`.
- [x] Interface boundaries: audio pre-processing, capture policy, local-first
      recognition, rescue recognition, and canonicalization are treated as
      explicit service boundaries with bounded fallback and truthful degraded
      behavior.
- [x] Structured results: the plan extends structured command-recognition
      payloads and keeps command execution under the existing structured result
      contract rather than adding free-form side paths.
- [x] Quality gates: the plan includes automated tests, benchmark fixtures,
      metadata-safe telemetry, smoke validation, and measurable latency and
      capture-completeness targets.

### Post-Design Re-Check

- [x] Phase 0 research resolves capture-profile placement, VAD and endpointing
      strategy, local-first and rescue routing, dictionary bias behavior, and
      privacy-safe qualification evidence without leaving blocking ambiguity.
- [x] Data model defines audio capture profiles, capture attempts, hybrid
      recognition results, canonicalization outcomes, and benchmark fixtures
      with validation rules and state transitions.
- [x] Contracts define the machine-readable capture profile, capture metadata,
      hybrid recognition result, and canonicalization payloads consumed across
      the runtime pipeline.
- [x] Quickstart defines repeatable validation for clipping recovery, noisy and
      bilingual command resolution, closed-vocabulary filtering, simplified
      degraded mode, and Raspberry Pi qualification evidence.
- [x] No constitution violations require Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/014-audio-stt-canonicalization/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- audio-capture-profile-contract.md
|   |-- capture-quality-metadata-contract.md
|   |-- hybrid-command-recognition-contract.md
|   `-- transcript-canonicalization-contract.md
`-- tasks.md
```

### Source Code (repository root)

```text
main.py
controllers/
core/
|-- audio/
|-- speech/
settings/
tts/
ui/
tests/
docs/
scripts/
```

**Structure Decision**: Keep Phase 14 inside the existing repository layout.
Add a small `core/audio/` package for reusable pre-processing and capture
profile logic, keep STT orchestration centered in `core/stt.py` and
`core/speech/legacy_stt.py`, expand `core/assistant_runtime.py` and
`core/command_post_processing.py` for capture-aware decisions and
canonicalization, and keep policy defaults in `settings/settings_manager.py`
and `settings/profile_store.py`. No new top-level package or UI-owned runtime
path is justified.

## Complexity Tracking

No constitution violations are expected for this feature. The design remains
incremental, runtime-first, adapter-oriented, accessibility-safe, and
measurable through the current speech-provider architecture.
