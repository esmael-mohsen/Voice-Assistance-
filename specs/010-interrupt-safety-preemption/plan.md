# Implementation Plan: Interrupt Safety and TTS Preemption

**Branch**: `[010-interrupt-safety-preemption]` | **Date**: 2026-04-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-interrupt-safety-preemption/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Keep it
aligned with `.specify/memory/constitution.md`.

## Summary

Harden interrupt safety by expanding approved Arabic and English stop or cancel
phrase handling, making TTS playback genuinely preemptible instead of only
interrupt-aware in metadata, propagating accepted interrupts through runtime
and in-flight work handling, and measuring preemption latency through the
existing recovery-outcome observability path.

## Technical Context

**Language/Version**: Python 3.12.4  
**Primary Dependencies**: Existing runtime stack (`SpeechRecognition`,
`edge-tts`, `playsound`, `pytest`) plus current runtime observability and
critical prompt infrastructure in `core/assistant_runtime.py`,
`core/command_models.py`, `core/release_metrics.py`, and
`core/critical_prompts.py`  
**Storage**: No new persisted datastore; interrupt vocabulary, playback
session state, and in-flight cancellation markers remain in-memory, while
approved spoken guidance continues to use the critical prompt catalog in
`settings/user_profile.json`  
**Testing**: `pytest` unit, integration, and smoke coverage for bilingual
interrupt detection, preemptible speech playback, safe runtime recovery,
latency recording, weak-network degraded recovery, and best-effort
cancellation behavior  
**Target Platform**: Windows desktop debug runtime and headless console mode as
the wearable-reference execution path  
**Project Type**: Python voice assistant with runtime-first orchestration,
provider-backed speech services, and assistive safety constraints  
**Performance Goals**: Accepted interrupts stop audible speech within 500 ms
in at least 95% of validation runs, no validated case exceeds 1 second, and
accepted interrupt flows always recover to a safe state without unbounded
playback or follow-up speech  
**Constraints**: No rewrite; preserve layered architecture; keep runtime logic
out of `ui/`; support Arabic and English interrupt phrases regardless of the
active prompt language; maintain structured outcomes and approved critical
prompt routing; avoid introducing provider-specific shortcuts without an
explicit speech-service boundary; keep `settings/settings_manager.py` limited
to speech dispatch and runtime configuration handoff rather than interrupt
decision logic; design for best-effort cancellation when work is already near
completion; preserve local interrupt preemption during weak-network or
provider-stall conditions; use the canonical Phase 10 interrupt vocabulary of
English `stop`, `cancel`, `stop now` and Arabic `قف`, `توقف`, `إلغاء`  
**Scale/Scope**: Update interrupt handling in `core/assistant_runtime.py`,
speech playback behavior in `tts/tts_engine.py`, runtime speech dispatch
handoff in `settings/settings_manager.py`, interrupt/result models in
`core/command_models.py`, prompt surfaces in `core/critical_prompts.py`, and
interrupt-focused validation under `tests/unit/`, `tests/integration/`, and
`tests/smoke/`. The moderate-load validation profile for this feature is one
active 5-second-or-longer TTS response plus one concurrent thinking or
safe-to-cancel capability operation with structured logging enabled in the same
runtime session.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check

- [x] Incremental change: the plan stays within the existing runtime, TTS,
      settings, and test layers and does not require a top-level rewrite.
- [x] Runtime/UI separation: interrupt logic remains anchored in runtime and
      speech-service code, not `ui/`.
- [x] Interface boundaries: interrupt handling is planned around explicit
      runtime, speech-service, and structured outcome boundaries rather than ad
      hoc UI or controller shortcuts.
- [x] Weak-network handling: provider-backed interrupt flows define degraded
      behavior so local speech preemption still works when remote work stalls.
- [x] Structured results: accepted and ignored interrupts continue to report
      machine-readable outcome data through structured runtime recovery events.
- [x] Quality gates: unit, integration, smoke, logging, and latency validation
      are all part of the design scope.

### Post-Design Re-Check

- [x] Phase 0 research resolves interrupt vocabulary scope, preemption
      semantics, best-effort cancellation behavior, and latency validation
      without leaving blocking ambiguities.
- [x] Data model defines interrupt vocabulary, detection results, playback
      sessions, in-flight work context, preemption outcomes, and latency
      records.
- [x] Contracts define the machine-readable interrupt signal and preemption
      outcome payloads used by runtime logic and regression validation.
- [x] Quickstart defines repeatable bilingual validation for speech
      interruption, in-flight cancellation, observability, and latency bounds.
- [x] No constitution violations require Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/010-interrupt-safety-preemption/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- interrupt-signal-contract.md
|   `-- preemption-outcome-contract.md
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
```

**Structure Decision**: Keep interrupt hardening inside the existing runtime,
speech-service, and observability layers. If a shared interrupt-policy helper
is needed, keep it as a small module under `core/` rather than creating a new
top-level package. `settings/settings_manager.py` remains responsible only for
runtime settings and speech dispatch handoff, while interrupt acceptance,
recovery decisions, degraded-mode handling, and best-effort cancellation stay
owned by `core/assistant_runtime.py`, `tts/tts_engine.py`, and structured
result models.

## Complexity Tracking

No constitution violations are expected for this feature. The design remains
incremental, runtime-first, accessibility-oriented, and measurable within the
current repository layout.
