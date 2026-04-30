# Implementation Plan: Confirmation, Clarification, and Command Robustness

**Branch**: `[009-confirmation-command-robustness]` | **Date**: 2026-04-20 |
**Spec**: [spec.md](./spec.md)
**Input**: Feature specification from
`/specs/009-confirmation-command-robustness/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Keep it
aligned with `.specify/memory/constitution.md`.

## Summary

Harden protected command confirmation and parameter clarification by replacing
brittle exact-match parsing with shared token and phrase-family dialog
interpretation, adding explicit supported-choice clarification prompts with
bounded retries, and isolating confirmation and clarification state from stale
follow-up context so safe behavior remains deterministic across runtime flows.

## Technical Context

**Language/Version**: Python 3.12.4  
**Primary Dependencies**: Existing runtime stack (`SpeechRecognition`,
`rapidfuzz`, `edge-tts`, `playsound`, `customtkinter`, `pytest`) plus Python
standard library `re` and current critical prompt catalog and runtime settings
modules for bilingual dialog handling  
**Storage**: No new persisted datastore; dialog vocabulary and temporary
session state remain in-memory in `core/command_models.py` and
`core/resolver.py`; approved prompt text remains in
`settings/user_profile.json` and the critical prompt catalog; repository-hosted
tests and docs artifacts capture contracts and validation evidence  
**Testing**: `pytest` unit, integration, and smoke coverage for phrase-family
classification, protected confirmation safety, clarification retry bounds,
follow-up isolation, and bilingual prompt integrity  
**Target Platform**: Windows desktop debug runtime and the headless console
path used as the wearable-reference execution mode  
**Project Type**: Python voice assistant with runtime-first architecture and a
bilingual command dialog layer  
**Performance Goals**: Keep confirmation and clarification interpretation local
and deterministic with no network dependency; add no more than about 50 ms of
resolver-side decision overhead per utterance in regression checks; always
terminate clarification within one initial prompt plus two retries  
**Constraints**: No rewrite; preserve layered architecture; keep dialog logic
out of `ui/`; do not weaken protected-command safeguards; negative or cancel
cues must win over affirmative cues when mixed; keep Arabic and English
guidance aligned with approved prompt surfaces; maintain structured command
results and session-context safety  
**Scale/Scope**: Update `core/resolver.py`, `core/assistant_runtime.py` for
shared onboarding or confirmation reuse only, `core/command_models.py`,
`core/critical_prompts.py`, optionally a small shared `core/dialog_policy.py`
helper, and targeted tests and docs covering protected confirmations,
clarification flows, and follow-up state isolation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check

- [x] Incremental change: the plan stays inside the existing `core/`,
      `settings/`, `tests/`, and docs layers and avoids any rewrite or new
      top-level subsystem.
- [x] Runtime/UI separation: confirmation and clarification behavior remains in
      runtime, resolver, and prompt-catalog code rather than moving into
      `ui/`.
- [x] Interface boundaries: dialog interpretation, pending-session state, and
      clarification outcomes are planned as explicit contracts instead of
      scattered string checks.
- [x] Structured results: command and dialog flows will continue exposing
      `spoken_text`, `status`, `payload`, and `error_code`, extended with
      confirmation and clarification outcome metadata where needed.
- [x] Quality gates: unit, integration, and smoke validation plus structured
      regression coverage for cancellations, retry bounds, and follow-up
      isolation are part of the design.

### Post-Design Re-Check

- [x] Phase 0 research resolves phrase-family matching, safe precedence,
      clarification retry policy, prompt-surface reuse, and follow-up isolation
      without leaving unresolved clarifications.
- [x] Data model defines confirmation vocabulary, dialog interpretation
      results, pending confirmation state, clarification sessions, follow-up
      context state, and structured dialog outcomes.
- [x] Contracts define machine-readable confirmation-decision and
      clarification-session payloads used by resolver logic, runtime flows, and
      regression tests.
- [x] Quickstart defines repeatable validation for Arabic and English phrase
      variants, mixed yes and cancel input, bounded clarification retries, and
      stale follow-up clearing.
- [x] No constitution violations require Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/009-confirmation-command-robustness/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- clarification-session-contract.md
|   `-- confirmation-decision-contract.md
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

**Structure Decision**: Keep dialog-robustness work in the existing resolver,
runtime, prompt-catalog, and command-model layers. Add at most one small shared
dialog interpretation helper if reuse between resolver and onboarding would
otherwise duplicate safety-critical phrase parsing.

## Complexity Tracking

No constitution violations are expected for this feature. The design remains
incremental, runtime-first, accessibility-oriented, and fully testable within
the current repository structure.
