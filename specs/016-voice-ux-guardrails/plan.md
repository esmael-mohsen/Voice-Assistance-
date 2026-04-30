# Implementation Plan: Continuous Turn-Taking, Closed-Vocabulary Guardrails, and Pilot-Grade Voice UX

**Branch**: `[017-voice-ux-guardrails]` | **Date**: 2026-04-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/016-voice-ux-guardrails/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Keep it
aligned with `.specify/memory/constitution.md`.

## Summary

Make guided voice interactions feel natural and controlled by extracting
turn-taking decisions from the current runtime into a dedicated coordinator,
centralizing a bilingual closed-vocabulary registry, tightening prompt-echo,
retry, and name-confirmation guardrails, and recording pilot-grade UX evidence
through lightweight local artifacts without weakening existing safety flows.

## Technical Context

**Language/Version**: Python 3.12.4  
**Primary Dependencies**: Existing runtime stack (`SpeechRecognition`,
`rapidfuzz`, `edge-tts`, `playsound`, `customtkinter`) plus current dialog and
speech modules in `core/assistant_runtime.py`, `core/dialog_policy.py`,
`core/stt.py`, `core/resolver.py`, `core/command_models.py`,
`core/critical_prompts.py`, `settings/settings_manager.py`,
`settings/profile_store.py`, `tts/tts_engine.py`, and the existing release
artifact helpers under `core/release_*.py`  
**Storage**: Existing persisted runtime profile and prompt catalog in
`settings/user_profile.json`; runtime settings persistence via
`settings/profile_store.py`; lightweight pilot UX evidence stored locally under
candidate artifact directories such as `artifacts/<run-id>/`; no new external
datastore  
**Testing**: `pytest` unit, integration, and smoke coverage for turn-taking
windows, closed-vocabulary validation, prompt-echo suppression, protected-flow
interruption boundaries, retry exhaustion fallback, name capture and
confirmation, and pilot UX evidence generation; `python -m compileall` and
`ruff check .` remain part of the validation path  
**Target Platform**: Windows desktop debug runtime and headless console mode as
the reference execution path, with Raspberry Pi 4 Model B as the wearable
deployment target  
**Project Type**: Python voice assistant with runtime-first orchestration,
bilingual guided dialog flows, assistive safety constraints, and structured
runtime outcomes  
**Performance Goals**: At least 90% of approved onboarding and settings answers
spoken during allowed barge-in windows are accepted without repeat prompts; at
least 95% of closed-vocabulary turns for language, voice, speed, and
yes/no/cancel resolve correctly within two turns; prompt echo stays below 1
false accepted answer per 100 guided turns; at least 90% of first-run
onboarding benchmark journeys complete without manual restart; 100% of pilot UX
validation runs capture completion status, retries, barge-in acceptance,
prompt-echo suppressions, out-of-domain rejections, and fallback or exit
reason  
**Constraints**: Preserve the current layered architecture; keep runtime
authority in `core/` rather than `ui/`; treat `core/critical_prompts.py` and
the profile-backed prompt catalog as the prompt source of truth; allow only
approved global safety commands to preempt closed-vocabulary turns; keep
protected confirmations, shutdown, and destructive flows stricter than normal
guided prompts; exclude raw user utterances from default pilot evidence; do not
introduce unrestricted always-open conversation or an LLM-first control path  
**Scale/Scope**: Refine turn-taking, onboarding, prompt playback coordination,
and guided-input handling in `core/assistant_runtime.py`; keep yes/no/cancel
interpretation in `core/dialog_policy.py`; align closed-vocabulary and
fallback-aware resolution behavior in `core/stt.py`, `core/resolver.py`, and
`core/command_models.py`; add small focused runtime modules such as
`core/turn_taking.py` and `core/closed_vocabulary.py`; extend prompt surfaces
through `core/critical_prompts.py` and settings defaults through
`settings/settings_manager.py` and `settings/profile_store.py`; shape pilot UX
evidence through `core/release_artifacts.py`, `core/release_metrics.py`, and
`core/release_models.py`; add validation coverage under `tests/`, fixture
guidance under `tests/fixtures/dialog/`, and reviewer guidance in
`docs/release/checklist.md`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check

- [x] Incremental change: the design factors existing onboarding and guided
      dialog behavior out of `core/assistant_runtime.py` into small runtime
      helpers instead of introducing a parallel speech stack.
- [x] Runtime/UI separation: turn-taking, closed-vocabulary policy, retry
      behavior, and pilot UX evidence stay runtime-owned in `core/`,
      `settings/`, and `tts/`, not in `ui/`.
- [x] Interface boundaries: turn-taking coordination, closed-vocabulary
      registry lookups, STT filtering, prompt catalog resolution, and pilot
      evidence shaping remain behind explicit runtime contracts with bounded
      fallback behavior.
- [x] Structured results: guided dialog decisions, name-confirmation outcomes,
      prompt-echo suppressions, and pilot UX validation evidence are planned as
      structured machine-readable payloads rather than ad hoc strings only.
- [x] Quality gates: the plan includes automated tests, smoke validation,
      prompt-safety checks, and measurable journey outcomes for barge-in,
      retries, and pilot UX evidence.

### Post-Design Re-Check

- [x] Phase 0 research resolves coordinator placement, closed-vocabulary
      registry boundaries, prompt-echo strategy, retry exhaustion behavior,
      explicit name confirmation, and field-safe pilot evidence storage without
      leaving blocking ambiguity.
- [x] Data model defines turn-taking windows, closed-vocabulary contexts,
      guided dialog sessions, prompt-echo signals, name candidates, and pilot
      UX evaluation runs with validation rules and state transitions.
- [x] Contracts define machine-readable turn-taking, closed-vocabulary, guided
      dialog, and pilot validation payloads consumed across runtime and test
      flows.
- [x] Quickstart defines repeatable validation for allowed barge-in,
      protected-flow blocking, closed-vocabulary rejection, prompt-echo
      suppression, safe fallback continuation, and pilot evidence review.
- [x] No constitution violations require Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/016-voice-ux-guardrails/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- turn-taking-window-contract.md
|   |-- closed-vocabulary-context-contract.md
|   |-- guided-dialog-outcome-contract.md
|   `-- pilot-voice-ux-evaluation-contract.md
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
|-- fixtures/
docs/
|-- release/
scripts/
```

**Structure Decision**: Keep Phase 16 inside the current runtime, settings,
prompt-catalog, release-artifact, and test layout. `core/assistant_runtime.py`
remains the authority for session transitions and prompt playback
coordination, while a small `core/turn_taking.py` module owns prompt-window
and barge-in decisions, and a small `core/closed_vocabulary.py` module owns
the registry of allowed guided-answer sets. `core/dialog_policy.py` remains
the shared yes/no/cancel interpreter, `core/stt.py` continues to apply
closed-choice recognition constraints, `core/resolver.py` preserves
protected-flow handling, `core/release_artifacts.py`,
`core/release_metrics.py`, and `core/release_models.py` remain the pilot
evidence shaping surfaces, and `core/critical_prompts.py` plus `settings/`
remain the prompt and fallback authority. Validation fixtures stay under
`tests/fixtures/dialog/`, release-review guidance stays in
`docs/release/checklist.md`, and no new top-level package or UI-owned dialog
runtime is justified.

## Complexity Tracking

No constitution violations are expected for this feature. The design remains
incremental, runtime-first, adapter-oriented, accessibility-safe, and
measurable through the existing repository layout.
