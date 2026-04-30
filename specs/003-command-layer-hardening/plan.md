# Implementation Plan: Command Layer Hardening

**Branch**: `[003-command-layer-hardening]` | **Date**: 2026-04-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-command-layer-hardening/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Keep it
aligned with `.specify/memory/constitution.md`.

## Summary

Harden the existing bilingual command layer without expanding scope by moving
from one global fuzzy-match pass plus raw resolver returns to a risk-aware
pipeline with categorized command metadata, stronger validation for system
commands, structured command results, and one-shot follow-up session context.
The implementation stays inside the current runtime architecture so GUI and
console flows continue to share the same core command behavior.

## Technical Context

**Language/Version**: Python 3.12.4  
**Primary Dependencies**: `rapidfuzz` for matching, `pytest` for regression
coverage, existing runtime/settings layers in `core.assistant_runtime` and
`settings.settings_manager`, existing controller entry points in
`controllers.mock_controllers`  
**Storage**: In-memory command session context for follow-up and confirmation
state; no new persisted storage beyond existing profile/settings JSON  
**Testing**: `pytest` unit coverage for parser and resolver logic, integration
coverage for dispatch/runtime parity, smoke validation for representative GUI
and console command flows, baseline timing capture for wake, STT, TTS, command
dispatch, and provider-failure recovery, plus `python -m compileall`  
**Target Platform**: Windows desktop GUI via `python main.py` and console or
headless runtime via `python main.py --console`  
**Project Type**: Python voice assistant with a shared runtime and bilingual
command-understanding layer  
**Performance Goals**: Achieve at least 90% curated regression accuracy across
Arabic and English priority commands, maintain 0 unintended protected-system
activations in near-match coverage, keep command handling within the current
in-process runtime loop with at most one clarification turn, establish
representative baseline timings for wake detection, STT response, TTS start,
command dispatch completion, and recoverable provider-failure handling, and do
not regress median command-dispatch latency by more than 10% against the
captured baseline during feature validation  
**Constraints**: Do not add new commands in this phase, preserve runtime or UI
separation, keep command behavior equivalent across GUI and console modes,
require explicit confirmation for high-consequence system commands, use
stricter validation for lower-risk system commands, ask for clarification once,
and clear follow-up context after one immediate use; preserve the existing
provider fallback or degraded-mode path under weak-network or provider
instability; do not introduce any new non-verbal feedback dependency for core
command flows  
**Scale/Scope**: `core/parser.py`, `core/resolver.py`, `core/dispatcher.py`,
shared command models in `core/command_models.py`, runtime result handling in
`core/assistant_runtime.py`, and new regression coverage under `tests/unit`,
`tests/integration`, and `tests/smoke`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check

- [x] Incremental change: the plan keeps the current layered structure and
      improves parser, resolver, dispatcher, and runtime boundaries in place
      rather than introducing a rewrite.
- [x] Runtime/UI separation: command parsing, validation, routing, and result
      modeling remain owned by `core/`; `ui/` stays an observer bridge only.
- [x] Interface boundaries: the feature introduces an explicit command result
      contract between parser, resolver, dispatcher, and runtime instead of
      letting free-form strings leak across layers.
- [x] Structured results: the design formalizes `spoken_text`, `status`,
      `payload`, and `error_code`, plus the validation states needed for
      clarification, rejection, and confirmation.
- [x] Quality gates: the plan includes unit, integration, and smoke tests,
      structured logging of command outcomes, and regression coverage tied to
      measurable accuracy and safety goals.

### Post-Design Re-Check

- [x] Research defines risk-based intent validation, command grouping, and
      confirmation policy without expanding the supported command set.
- [x] Data model covers parsed intent, command resolution, execution result,
      and single-follow-up session context required by the clarified spec.
- [x] Contracts describe the command-processing boundary clearly enough for
      runtime and downstream consumers to rely on structured outcomes.
- [x] Quickstart exercises protected system commands, everyday assistant
      commands, and high-value capability commands across GUI and console paths.
- [x] No constitution violations require `Complexity Tracking` entries.

## Project Structure

### Documentation (this feature)

```text
specs/003-command-layer-hardening/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- command-processing-runtime.md
`-- tasks.md
```

### Source Code (repository root)

```text
main.py
controllers/
core/
|-- assistant_runtime.py
|-- command_models.py
|-- dispatcher.py
|-- parser.py
`-- resolver.py
settings/
ui/
tests/
|-- integration/
|   `-- test_command_dispatch.py
|-- smoke/
|   `-- test_command_layer_quickstart.py
`-- unit/
    |-- test_parser.py
    `-- test_resolver.py
docs/
```

**Structure Decision**: Keep the existing repository layout and concentrate the
hardening work inside `core/` plus tests. Add one small shared-model module for
command contracts if needed, while keeping runtime ownership in
`core.assistant_runtime` and leaving `ui/` free of business logic.

## Complexity Tracking

No constitution violations are expected for this feature. The design stays
within the current runtime architecture and uses small focused additions rather
than a broader command-system rewrite.
