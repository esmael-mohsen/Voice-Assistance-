# Implementation Plan: Wake Strategy and Low-Power Standby

**Branch**: `[011-wake-strategy-standby]` | **Date**: 2026-04-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/011-wake-strategy-standby/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Keep it
aligned with `.specify/memory/constitution.md`.

## Summary

Make standby truly wake-policy driven for wearable use by moving the runtime
away from always-on free-form STT while idle, honoring configured wake modes
for keyword, hardware-trigger, and dev-only STT fallback, and capturing wake
selection, rejected wake attempts, degraded standby behavior, and wake latency
through structured runtime outcomes and release baselines while preserving
truthful weak-network behavior for any provider-backed wake path.

## Technical Context

**Language/Version**: Python 3.12.4  
**Primary Dependencies**: Existing runtime stack (`SpeechRecognition`,
`edge-tts`, `playsound`, `pytest`) plus current wake interfaces and provider
resolution logic in `core/assistant_runtime.py`,
`core/speech/interfaces.py`, `core/speech/provider_registry.py`,
`core/speech/provider_resolver.py`, and existing release metrics helpers in
`core/release_metrics.py`  
**Storage**: Existing persisted runtime profile in `settings/user_profile.json`
and `settings/profile_store.py`; no new datastore. Wake policy, standby
session state, and wake-attempt tracking remain in-memory, while baselines and
thresholds continue to use repository-hosted files already used by release
validation  
**Testing**: `pytest` unit, integration, and smoke coverage for wake-mode
selection, production vs development guardrails, degraded standby behavior,
headless parity, and wake-to-listening / listening-to-response latency
baselines  
**Target Platform**: Windows desktop debug runtime and headless console mode as
the wearable-reference execution path  
**Project Type**: Python voice assistant with runtime-first orchestration,
replaceable speech services, and assistive wearable constraints  
**Performance Goals**: In the defined light-load scenario of 10 sequential wake
cycles, at least 95% of accepted wake events reach listening within 1.5
seconds of the wake signal, at least 95% of successful wake flows begin the
first assistant response within 2.5 seconds after listening starts, and 100%
of disallowed STT wake attempts in production-like mode remain rejected  
**Constraints**: No rewrite; preserve layered architecture; keep wake policy
logic out of `ui/`; do not place feature workflow logic in
`settings/settings_manager.py`; production-like standby must not depend on
open-ended STT wake when `stt_wake_allowed_in_production=false`; noisy ambient
speech must not activate the assistant through forbidden STT wake; weak-network
or provider-unavailable wake paths must degrade safely with one-time guidance;
headless and GUI runtime entry points must honor the same wake policy and
produce the same structured outcomes; validate Phase 11 against the canonical
wake vocabulary `hi egb` and `مرحبا` until a hardware-specific catalog exists  
**Scale/Scope**: Refine wake-mode resolution and standby execution in
`core/assistant_runtime.py`, `core/speech/provider_resolver.py`,
`core/speech/provider_registry.py`, `core/speech/legacy_wake.py`, and
`core/speech/speakkit_wake.py`, keep persisted wake policy in
`settings/user_profile.json` and related settings models, extend wake or
standby observability and latency capture in existing runtime metrics paths,
and add wake-policy validation under `tests/unit/`, `tests/integration/`, and
`tests/smoke/`, including `tests/integration/test_gui_runtime_bridge.py`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check

- [x] Incremental change: the plan stays within the existing runtime, speech,
      settings, and test layers and does not require a top-level rewrite.
- [x] Runtime/UI separation: wake-policy and standby logic remain owned by
      runtime and speech-service boundaries, not `ui/`.
- [x] Interface boundaries: wake selection and standby execution stay behind
      runtime and wake-service contracts, with explicit degraded behavior when
      the configured wake source is unavailable or provider-backed wake paths
      encounter weak-network conditions.
- [x] Safety and accessibility: the plan keeps wearable-first non-visual
      behavior, bounded degraded guidance, noisy-input rejection, and dev vs
      production guardrails explicit.
- [x] Quality gates: structured logging, unit/integration/smoke validation,
      and measurable wake latency baselines are all part of the design scope.

### Post-Design Re-Check

- [x] Phase 0 research resolves the standby waiting strategy, dev-only STT
      fallback rules, degraded notification cadence, and wake latency scenario
      without leaving blocking ambiguities.
- [x] Data model defines wake policy, standby session, wake attempts, wake
      outcomes, and latency baseline records.
- [x] Contracts define machine-readable wake selection and standby outcome
      payloads used by runtime logic and validation.
- [x] Quickstart defines repeatable validation for production-like wake,
      development fallback, degraded standby behavior, headless parity, and
      latency checks.
- [x] No constitution violations require Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/011-wake-strategy-standby/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- standby-wake-outcome-contract.md
|   `-- wake-mode-selection-contract.md
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

**Structure Decision**: Keep Phase 11 inside the current runtime and speech
provider layers. `core/assistant_runtime.py` remains the authority for standby
execution and state transitions, `core/speech/provider_resolver.py` owns wake
policy selection and degraded-mode reasoning, persisted wake preferences remain
in `settings/`, `core/speech/provider_registry.py` and the concrete wake
adapters expose wake availability and waiting boundaries, and validation stays
under `tests/`. If a shared helper is needed, keep it as a small runtime or
speech module under `core/` rather than adding a new top-level package.

## Complexity Tracking

No constitution violations are expected for this feature. The design remains
incremental, runtime-first, adapter-oriented, accessibility-aware, and fully
measurable within the current repository layout.
