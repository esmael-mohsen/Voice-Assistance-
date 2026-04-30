# Implementation Plan: Wake Reliability, Telemetry, and Raspberry Pi Performance Qualification

**Branch**: `[016-wake-telemetry-qualification]` | **Date**: 2026-04-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/015-wake-telemetry-qualification/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Keep it
aligned with `.specify/memory/constitution.md`.

## Summary

Harden the existing wake and speech runtime into a wearable-ready operational
baseline by refining wake acceptance and recovery rules, coordinating safe
barge-in and prompt playback behavior, emitting lightweight structured speech
telemetry including command-confidence and recovery signals, and adding a
repeatable Raspberry Pi 4 qualification plus release gate workflow that uses
local artifacts by default and real hardware evidence for pilot approval.

## Technical Context

**Language/Version**: Python 3.12.4  
**Primary Dependencies**: Existing runtime stack (`SpeechRecognition`,
`rapidfuzz`, `edge-tts`, `playsound`, `customtkinter`) plus current wake and
speech service boundaries in `core/wake_word.py`, `core/speech/legacy_wake.py`,
`core/speech/speakkit_wake.py`, `core/assistant_runtime.py`, `core/stt.py`,
`tts/tts_engine.py`, `core/release_gates.py`, `core/release_metrics.py`,
`core/release_models.py`, and `core/runtime_diagnostics.py`  
**Storage**: Existing persisted runtime profile in `settings/user_profile.json`
and `settings/profile_store.py`; repository-hosted release documentation in
`docs/release/`; structured telemetry summaries and qualification evidence
stored locally under candidate artifact directories such as
`artifacts/<run-id>/`; no new external datastore  
**Testing**: `pytest` unit, integration, and smoke coverage for wake scoring,
confirmation-window behavior, safe barge-in, repeated-fault recovery,
telemetry-event shaping, benchmark replay, Raspberry Pi 4 qualification, GUI
parity, and release-gate evaluation; `python -m compileall` and `ruff check .`
remain part of the validation path  
**Target Platform**: Windows desktop debug runtime and headless console mode as
the reference execution path, with Raspberry Pi 4 Model B as the release
qualification target  
**Project Type**: Python voice assistant with runtime-first speech adapters,
assistive wearable constraints, structured runtime outcomes, and release
qualification gates  
**Performance Goals**: At least 95% of valid qualification wake attempts reach
listening within 1.2 seconds; at least 98% of benchmark and qualification runs
emit complete wake plus latency telemetry; ordinary speech-loop failures reset
to standby after no more than three consecutive faults; Raspberry Pi 4
qualification requires a 30-minute repeated wake-cycle run with standby median
CPU at or below 15%, no unplanned runtime shutdowns, and no sustained thermal
condition that takes the assistant out of service  
**Constraints**: Preserve the current layered architecture; keep runtime logic
in `core/` and `tts/`; do not create a heavy always-listening production mode;
keep wake behavior adapter-oriented and future hardware-trigger compatible; use
only lightweight local telemetry by default; keep risky prompts protected from
barge-in until spoken once; distinguish CI replay validation from real Pi
hardware approval; maintain safe headless behavior and truthful degraded-mode
messaging  
**Scale/Scope**: Refine wake behavior in `core/wake_word.py`,
`core/speech/legacy_wake.py`, and `core/speech/speakkit_wake.py`; coordinate
wake, listening, prompt playback, and repeated-fault reset behavior in
`core/assistant_runtime.py`, `core/stt.py`, and `tts/tts_engine.py`; extend
structured telemetry and qualification reporting through
`core/release_gates.py`, `core/release_models.py`, and small runtime helper
modules under `core/`; align qualification thresholds in
`settings/release_thresholds.json`; update release operator docs in
`docs/release/startup.md` and `docs/release/troubleshooting.md`; add
benchmark, telemetry, and qualification validation under `tests/`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check

- [x] Incremental change: the plan extends existing wake, runtime, TTS,
      release, and documentation surfaces rather than rewriting the speech
      stack.
- [x] Runtime/UI separation: wake reliability, barge-in coordination,
      telemetry, and recovery logic remain runtime-owned in `core/` and
      `tts/`, not `ui/`.
- [x] Interface boundaries: wake adapters, telemetry sinks, replay scenarios,
      and release-gate evaluation stay behind explicit service contracts with
      fallback and degraded behavior.
- [x] Structured results: wake outcomes, recovery results, telemetry events,
      qualification runs, and release-gate decisions are planned as structured
      machine-readable payloads rather than plain logs only.
- [x] Quality gates: automated tests, structured logging, smoke validation,
      replay benchmarking, and measurable latency and Raspberry Pi resource
      targets are included in scope.

### Post-Design Re-Check

- [x] Phase 0 research resolves wake confirmation policy, safe barge-in scope,
      repeated-fault recovery, local telemetry evidence storage, and CI versus
      real-hardware qualification boundaries without leaving blocking
      ambiguity.
- [x] Data model defines wake policy profiles, wake attempts, speech-loop
      recovery, telemetry events, replay scenarios, qualification runs, and
      release-gate decisions with validation rules and state transitions.
- [x] Contracts define machine-readable wake, telemetry, recovery,
      qualification, and release-gate payloads consumed across runtime and
      validation flows.
- [x] Quickstart defines repeatable headless validation for wake hardening,
      safe barge-in, degraded recovery, telemetry replay, Raspberry Pi 4
      qualification, and release-gate evidence review.
- [x] No constitution violations require Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/015-wake-telemetry-qualification/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- wake-reliability-outcome-contract.md
|   |-- speech-telemetry-event-contract.md
|   |-- speech-loop-recovery-contract.md
|   |-- pi-qualification-run-contract.md
|   `-- speech-release-gate-contract.md
`-- tasks.md
```

### Source Code (repository root)

```text
main.py
controllers/
core/
|-- speech/
settings/
tts/
ui/
tests/
docs/
scripts/
```

**Structure Decision**: Keep Phase 15 inside the current runtime, wake, TTS,
release, and documentation layers. `core/assistant_runtime.py` remains the
authority for speech-loop transitions and repeated-fault reset behavior;
`core/wake_word.py` plus the concrete wake adapters remain the wake-evaluation
boundary; `tts/tts_engine.py` exposes prompt classes that drive safe barge-in;
telemetry and qualification helpers stay as small runtime modules under
`core/`; release approval remains centered in `core/release_gates.py`; and
operator guidance continues in `docs/release/`. No new top-level package is
justified.

## Complexity Tracking

No constitution violations are expected for this feature. The design remains
incremental, runtime-first, adapter-oriented, accessibility-safe, and fully
measurable through the existing repository layout.
