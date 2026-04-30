# Implementation Plan: Offline Truth and Network Policy Alignment

**Branch**: `[008-offline-policy-alignment]` | **Date**: 2026-04-20 | **Spec**:
[spec.md](./spec.md)
**Input**: Feature specification from
`/specs/008-offline-policy-alignment/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Keep it
aligned with `.specify/memory/constitution.md`.

## Summary

Make offline behavior truthful by correcting provider `requires_network`
metadata, introducing a probe-backed session connectivity state with a
development-only override that always resets to `auto` on startup, and routing
startup/runtime command decisions through one structured offline-policy path
that keeps guidance, logs, and runtime events aligned.

## Technical Context

**Language/Version**: Python 3.12.4  
**Primary Dependencies**: Existing runtime stack (`SpeechRecognition`,
`edge-tts`, `playsound`, `customtkinter`, `pytest`) plus Python standard
library `socket`, `time`, and current provider registry / critical prompt
modules for probe-backed connectivity and structured policy evaluation  
**Storage**: `settings/user_profile.json` for persisted user preferences,
speech-provider selection, and offline allowlist; runtime-only connectivity and
override session state held in `settings/settings_manager.py` and
`core/assistant_runtime.py`; repository-hosted tests and docs artifacts  
**Testing**: `pytest` unit, integration, and smoke coverage for provider
metadata truth, connectivity probe transitions, override reset behavior,
runtime offline-policy matrix, and startup/degraded guidance  
**Target Platform**: Windows desktop debug runtime and the headless console
path used as the wearable-reference execution mode  
**Project Type**: Python voice assistant with runtime-first architecture and
incremental feature delivery  
**Performance Goals**: Reflect connectivity loss or restoration in runtime
state and user guidance within 5 seconds of detection; bound uncertain probe
grace handling to 2 seconds or less before converging to offline-safe behavior;
avoid adding perceptible command latency when a fresh connectivity state is
already available  
**Constraints**: No rewrite; preserve layered architecture; keep runtime logic
out of `ui/`; avoid new external probe dependencies; keep manual override
development-only and session-scoped; treat general connectivity and
provider/service availability as separate signals; preserve Arabic and English
truthful guidance through approved prompt surfaces  
**Scale/Scope**: Update `core/speech/provider_registry.py`,
`core/speech/provider_resolver.py`, a small `core/speech/network_probe.py`
helper, `core/assistant_runtime.py`, `settings/settings_manager.py`,
`settings/profile_store.py`, existing release/diagnostic surfaces, and targeted
tests/docs for provider truth, probe state, override reset, and offline policy
matrix behavior

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check

- [x] Incremental change: the plan stays within the existing `core/`,
      `settings/`, `tests/`, and docs layers and avoids any rewrite or new
      top-level subsystem.
- [x] Runtime/UI separation: connectivity truth and offline-policy logic remain
      in runtime, settings, and speech-layer code rather than becoming `ui/`
      behavior.
- [x] Interface boundaries: provider metadata, connectivity probing, and
      offline-policy decisions are planned as explicit contracts instead of
      scattered booleans or embedded strings.
- [x] Structured results: runtime and resolver policy outcomes will continue to
      expose `spoken_text`, `status`, `payload`, and `error_code`, extended
      with connectivity and provider-truth metadata where needed.
- [x] Quality gates: unit, integration, and smoke validation plus structured
      diagnostics and measurable connectivity-state timing are part of the
      design.

### Post-Design Re-Check

- [x] Phase 0 research resolves provider network truth, session-scoped override
      behavior, probe strategy, structured policy reasons, and validation
      boundaries without leaving unresolved clarifications.
- [x] Data model defines provider connectivity profiles, connectivity state,
      probe results, provider availability snapshots, offline capability
      approvals, and offline-policy decisions.
- [x] Contracts define the runtime connectivity-state payload and the offline
      policy decision payload consumed by runtime flows, diagnostics, and
      regression tests.
- [x] Quickstart defines repeatable validation for startup reset behavior,
      probe uncertainty handling, and command-level offline truthfulness across
      providers and allowlisted capabilities.
- [x] No constitution violations require Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/008-offline-policy-alignment/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- connectivity-state-contract.md
|   `-- offline-policy-decision-contract.md
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

**Structure Decision**: Keep offline-truth logic in the existing speech,
runtime, and settings layers. Add only one small helper surface if needed
(`core/speech/network_probe.py`) and extend the current provider resolver,
critical prompt, and runtime event paths instead of introducing a new policy
framework.

## Complexity Tracking

No constitution violations are expected for this feature. The design remains
incremental, runtime-first, adapter-friendly, accessibility-oriented, and fully
testable within the current repository structure.
