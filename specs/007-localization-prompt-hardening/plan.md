# Implementation Plan: Localization Integrity and Prompt Hardening

**Branch**: `[007-localization-prompt-hardening]` | **Date**: 2026-04-19 | **Spec**:
[spec.md](./spec.md)
**Input**: Feature specification from
`/specs/007-localization-prompt-hardening/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Keep it
aligned with `.specify/memory/constitution.md`.

## Summary

Harden critical Arabic and English prompt delivery by keeping
`settings/user_profile.json` as the approved runtime baseline, routing startup,
onboarding, interrupt, offline, and protected-command confirmation surfaces
through approved prompt keys, and expanding release localization validation to
fail on mojibake patterns, embedded critical text, and missing same-language
emergency fallback signaling.

## Technical Context

**Language/Version**: Python 3.12.4  
**Primary Dependencies**: Existing runtime stack (`SpeechRecognition`,
`rapidfuzz`, `edge-tts`, `playsound`, `customtkinter`) plus current release
gate modules, `pytest`, and Python standard-library `json`/`re` support for
catalog normalization and deterministic integrity checks  
**Storage**: `settings/user_profile.json` as the runtime baseline for
`critical_prompt_catalog`, bootstrap fallback defaults in
`settings/settings_manager.py`, and repository-hosted tests/docs artifacts  
**Testing**: `pytest` unit/integration/smoke suites for settings normalization,
runtime prompt resolution, onboarding and confirmation flows, and release
localization regression coverage  
**Target Platform**: Windows desktop debug environment and the headless runtime
path used as the wearable-readiness source of truth  
**Project Type**: Python voice assistant with runtime-first architecture and
incremental feature delivery  
**Performance Goals**: Zero blocking prompt-integrity failures at release
time; 100% of critical runtime surfaces resolve through approved prompt keys;
same-language emergency fallback remains within the existing bounded speech
flow and emits integrity telemetry every time it is used  
**Constraints**: No rewrite; preserve layered architecture; keep runtime logic
out of `ui/`; keep `settings/user_profile.json` as the runtime baseline; keep
Arabic and English support for every critical prompt; do not fall back from
Arabic to English for corrupted critical prompts; keep detection rules
deterministic and regression-testable  
**Scale/Scope**: Update `core/assistant_runtime.py`, `core/resolver.py`,
`controllers/mock_controllers.py`, `settings/settings_manager.py`,
`settings/user_profile.json`, `core/release_localization.py`, and targeted
tests/docs for catalog normalization, critical surface bindings, runtime
fallback signaling, and release validation coverage

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check

- [x] Incremental change: the plan keeps the current layered structure and
      limits work to settings, runtime, resolver, controller, and release-gate
      surfaces already responsible for prompt delivery.
- [x] Runtime/UI separation: prompt hardening stays in runtime/settings/release
      layers and does not make `ui/` authoritative for spoken behavior.
- [x] Interface boundaries: critical prompt resolution, runtime fallback, and
      release validation are defined as explicit contracts rather than ad-hoc
      string handling.
- [x] Structured results: runtime prompt resolution and release validation are
      planned as structured payloads with `spoken_text`, `status`, `payload`,
      `error_code`, and integrity metadata where applicable.
- [x] Quality gates: tests, structured logging/signaling, smoke validation,
      and release-blocking localization checks are part of the design.

### Post-Design Re-Check

- [x] Phase 0 research resolves runtime baseline ownership, catalog repair,
      surface binding strategy, mojibake detection rules, and runtime fallback
      behavior.
- [x] Data model defines catalog entries, surface bindings, integrity
      findings, and runtime prompt resolution/fallback records.
- [x] Contracts define the approved catalog shape, runtime prompt resolution
      signal, and release localization validation result payloads.
- [x] Quickstart defines repeatable validation for catalog normalization,
      runtime critical-surface behavior, and release-gate regression coverage.
- [x] No constitution violations require Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/007-localization-prompt-hardening/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- critical-prompt-catalog-contract.md
|   `-- localization-validation-contract.md
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

**Structure Decision**: Keep prompt ownership inside the existing settings and
runtime layers. Add only small helper surfaces if needed (for example, a
surface registry under `core/`) and extend the existing
`core/release_localization.py` gate instead of introducing a new framework.

## Complexity Tracking

No constitution violations are expected for this feature. The plan remains
incremental, runtime-first, accessibility-oriented, and contract-driven.
