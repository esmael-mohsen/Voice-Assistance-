# Implementation Plan: Hybrid Command Recognition and Post-Processing

**Branch**: `[013-hybrid-command-recognition]` | **Date**: 2026-04-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/013-hybrid-command-recognition/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Keep it
aligned with `.specify/memory/constitution.md`.

## Summary

Improve command accuracy and safety by extending the existing STT and command
pipeline with a local-first recognition result contract, a dedicated command
post-processing stage for bilingual normalization and common STT substitutions,
and runtime confidence-decision logic that escalates to fallback recognition,
bounded confirmation, or safe refusal without breaking the current parser,
resolver, dispatcher, and protected-command safeguards.

## Technical Context

**Language/Version**: Python 3.12.4  
**Primary Dependencies**: Existing runtime stack (`SpeechRecognition`,
`rapidfuzz`, `edge-tts`, `playsound`, `customtkinter`) plus
`core.assistant_runtime`, `core.stt`, `core.parser`, `core.dispatcher`,
`core.resolver`, `core.command_models`, and `pytest`-based regression coverage  
**Storage**: Existing persisted profile in `settings/user_profile.json` for
runtime settings continuity and in-memory command/session state for recognition
decisions and follow-up handling; no new datastore  
**Testing**: `pytest` unit, integration, and smoke coverage for recognition
result shaping, confidence-band handling, fallback behavior, bilingual
normalization, protected-command safety, and telemetry metadata; `python -m
compileall` and `ruff check .` remain part of the release path  
**Target Platform**: Windows desktop debug runtime and headless console mode as
the wearable-reference execution path  
**Project Type**: Python voice assistant with runtime-first orchestration,
speech-provider adapters, bilingual command parsing, and assistive safety
gates  
**Performance Goals**: At least 90% of supported high-confidence commands
complete on the first attempt without extra prompts; 95% of high-confidence
local-first trials begin spoken response within 2 seconds; 95% of
fallback-assisted trials begin spoken response within 4 seconds; 100% of
low-confidence or ambiguous protected-command trials require explicit
affirmative confirmation before execution; latency evidence is measured on each
validation run across 30 local-first trials and 30 fallback-assisted trials,
using the 95th percentile from recognition start to spoken-response start  
**Constraints**: Preserve the current layered architecture; keep runtime logic
out of `ui/`; make the local path the first recognition option; keep fallback
selective and truthful under offline conditions; treat missing confidence as
uncertain; bound retries to one additional clarification cycle; preserve
existing protected-command safeguards; keep default telemetry metadata-only and
free of raw utterances; support Arabic, English, and mixed bilingual command
flows  
**Scale/Scope**: Extend STT result handling in `core/stt.py`; add a small
command post-processing boundary under `core/`; thread confidence-aware
recognition flow through `core/assistant_runtime.py`, `core/parser.py`,
`core/dispatcher.py`, `core/resolver.py`, `core/command_models.py`, and
`settings/settings_manager.py`; define an explicit local/fallback recognizer
boundary in `core/stt.py`; ensure mixed-language command handling is preserved
at the recognition and runtime-decision layers; and add Phase 13 validation
across `tests/unit/`, `tests/integration/`, and `tests/smoke/`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check

- [x] Incremental change: the plan extends the existing STT, parser, resolver,
      dispatcher, and runtime pipeline instead of introducing a replacement
      command stack.
- [x] Runtime/UI separation: command-recognition flow remains runtime-owned in
      `core/` and settings-owned in `settings/`, not GUI-owned in `ui/`.
- [x] Interface boundaries: local recognition, fallback recognition, and
      command post-processing are treated as explicit service boundaries with
      bounded fallback behavior and offline-safe handling.
- [x] Structured results: the design extends command contracts and preserves
      structured execution results rather than returning free-form strings.
- [x] Quality gates: the plan includes tests, telemetry, smoke validation, and
      measurable latency and safety targets for command recognition.

### Post-Design Re-Check

- [x] Phase 0 research resolves confidence handling, fallback escalation,
      normalization strategy, telemetry shape, and settings placement without
      leaving blocking ambiguities.
- [x] Data model defines command recognition results, post-processing outcomes,
      confidence-decision policy, and telemetry samples with validation rules
      and state transitions.
- [x] Contracts define the machine-readable recognition-result,
      post-processing, and confidence-decision payloads consumed across the
      runtime pipeline.
- [x] Quickstart defines repeatable validation for local-first execution,
      offline-safe fallback behavior, bilingual normalization, and
      protected-command confirmation.
- [x] No constitution violations require Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/013-hybrid-command-recognition/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- command-confidence-decision-contract.md
|   |-- command-post-processing-contract.md
|   `-- command-recognition-result-contract.md
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
```

**Structure Decision**: Keep Phase 13 inside the current repository layout.
`core/stt.py` remains the recognition entry surface, `core/assistant_runtime.py`
remains the confidence-aware orchestrator, `core/parser.py`,
`core/dispatcher.py`, and `core/resolver.py` remain the command understanding
and safety pipeline, and `settings/settings_manager.py` remains the runtime
configuration authority. Add only a small command post-processing module under
`core/` or `core/speech/` rather than a new top-level package.

## Complexity Tracking

No constitution violations are expected for this feature. The design remains
incremental, runtime-first, adapter-oriented, safety-aware, and measurable
through the current speech and command pipeline.
