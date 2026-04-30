# Implementation Plan: Cloud-Primary Command Recognition and Safety-Aware Fallback

**Branch**: `[019-cloud-command-recognition]` | **Date**: 2026-04-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/018-cloud-command-recognition/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Keep it
aligned with `.specify/memory/constitution.md`.

## Summary

Make command-mode recognition cloud-primary when explicitly enabled by using
the Phase 17 Google Cloud STT foundation, command-focused phrase hints, and
strict Vosk command grammar fallback, while preserving the existing
post-processing, parser, confidence policy, rescue recognition, dispatcher,
resolver, and public `CommandRecognitionResult` consumer contract.

The technical approach is incremental: adapt command candidate ordering and
metadata in `core/stt.py`, keep execution safety in `core/assistant_runtime.py`
and existing command policy, expand deterministic command hints in
`core/speech/phrase_hints.py`, and add tests that prove opt-in rollout,
no-match fallback recovery, protected-command confirmation, and zero default
PocketSphinx command candidates.

## Technical Context

**Language/Version**: Python 3.12.4  
**Primary Dependencies**: Existing runtime stack (`SpeechRecognition`,
`rapidfuzz`, `edge-tts`, `playsound`, `customtkinter`), Phase 17 optional
Google Cloud Speech boundary (`google-cloud-speech` when installed),
strict-Vosk support when available, deterministic phrase hints in
`core/speech/phrase_hints.py`, existing command post-processing/parser,
`pytest` for unit and integration validation, and `ruff`/`compileall` for local
quality checks  
**Storage**: No new persisted datastore; existing `settings/user_profile.json`
continues to hold runtime/profile settings only, cloud rollout controls remain
environment/config driven, and diagnostics/artifacts remain field-safe without
raw utterance or credential persistence by default  
**Testing**: `pytest` unit coverage for cloud command ordering, command phrase
hints, strict fallback no-match, confidence/fallback policy reuse,
wake-plus-command safety, and PocketSphinx exclusion; integration coverage for
`VoiceListener.listen_command_result`, `AssistantRuntime` rescue flow,
protected-command confirmation, disabled rollout parity, and field-safe
diagnostics; `python -m compileall core tests` and `python -m ruff check .`
remain release validation checks  
**Target Platform**: Windows desktop debug app and headless console runtime as
primary validation paths, while preserving Raspberry Pi/wearable constraints
for weak-network operation, bounded command latency, and non-visual recovery  
**Project Type**: Python voice assistant with provider-aware speech adapters,
structured command recognition results, accessibility-first voice UX, and
debug GUI parity  
**Performance Goals**: Cloud command attempt stays within the Phase 17
short-utterance timeout default of 3 seconds and at most one transient retry
inside the active command listen window; strict fallback remains bounded by the
same command window; unsupported fallback speech produces no usable transcript
in 100% of covered no-match fixtures; Arabic/bilingual and common command
fixtures record local-first baseline success and fallback-to-retry counts, then
prove strictly better cloud-primary counts for the same fixture sets; protected
command fixtures require confirmation in 100% of covered cases; default command
path contributes zero PocketSphinx candidates; diagnostics expose
source/fallback/confidence bands without raw utterance retention  
**Constraints**: Command-mode recognition only; wake recognition is deferred to
Phase 19; cloud-primary behavior remains opt-in and rollback-friendly; disabled
cloud behavior preserves existing command-recognition regression fixtures; do
not redesign `core.parser`, remove `process_command_transcript`, bypass
`AssistantRuntime._evaluate_confidence_decision`, bypass parser/confidence/
dispatcher/resolver safety, mutate profile language from detected cloud
language, use broad local dictation as fallback, or make PocketSphinx part of
the default command accuracy path  
**Scale/Scope**: Runtime changes are expected in `core/stt.py`,
`core/assistant_runtime.py`, `core/command_models.py` only if metadata labels
need extension, `core/command_post_processing.py` only if parser-rejection
signals need to be exposed for fallback decisions, `core/parser.py` only for
tests or existing catalog use, and `core/speech/phrase_hints.py` for
command-specific curated variants and hint caps; validation is under
`tests/unit/` and `tests/integration/`, with docs updates in `docs/STTInfo.md`
if behavior or rollout controls change

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check

- [x] Incremental change: the plan changes command-recognition ordering and
      metadata inside the existing listener/runtime flow without replacing
      `AssistantRuntime`, parser, dispatcher, resolver, provider IDs, or the
      command result contract.
- [x] Runtime/UI separation: command recognition, fallback decisions, phrase
      hints, diagnostics, and tests remain in `core/`, `core/speech/`,
      `settings/`, `docs/`, and `tests/`; no production behavior moves into
      `ui/`.
- [x] Interface boundaries: Google Cloud STT remains behind the Phase 17 speech
      adapter boundary with timeout, availability, failure codes, phrase hints,
      and strict fallback behavior.
- [x] Structured results: cloud candidates, strict fallback outcomes,
      recognition source metadata, alternatives, confidence bands, selected/
      detected language, and fallback decisions feed the existing structured
      `CommandRecognitionResult` and runtime diagnostics.
- [x] Quality gates: tests, field-safe logs, fake cloud responses, strict
      fallback fixtures, protected-command confirmation, disabled rollout
      regression, and latency/fallback checks are planned.

### Post-Design Re-Check

- [x] Phase 0 research resolves command ordering, fallback trigger ownership,
      confidence policy reuse, phrase hint governance, wake-plus-command
      handling, diagnostics/privacy, and validation boundaries.
- [x] Data model defines command recognition candidates, command phrase hint
      sets, fallback decisions, strict fallback outcomes, safety evaluations,
      and source metadata with validation rules and lifecycle states.
- [x] Contracts define command recognition result shape, fallback decision
      shape, command phrase hint shape, and command safety evaluation behavior.
- [x] Quickstart defines repeatable validation for opt-in rollout, cloud
      success/failure, low confidence, strict fallback success/no-match,
      parser rejection, protected-command confirmation, PocketSphinx exclusion,
      diagnostics, and disabled-cloud parity.
- [x] No constitution violations require Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/018-cloud-command-recognition/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- command-recognition-result-contract.md
|   |-- command-fallback-decision-contract.md
|   |-- command-phrase-hints-contract.md
|   `-- command-safety-evaluation-contract.md
`-- tasks.md
```

### Source Code (repository root)

```text
main.py
controllers/
core/
|-- assistant_runtime.py
|-- command_models.py
|-- command_post_processing.py
|-- parser.py
|-- stt.py
|-- speech/
|   |-- google_cloud_stt.py
|   `-- phrase_hints.py
settings/
tts/
ui/
tests/
|-- unit/
`-- integration/
docs/
```

**Structure Decision**: Keep the feature inside the existing runtime-first
speech and command layers. `core/stt.py` remains the public listener surface
and owns command candidate ordering, cloud/strict fallback invocation, source
metadata, and no-usable-transcript outcomes. `core/speech/google_cloud_stt.py`
continues to own provider-specific Google Cloud behavior from Phase 17.
`core/speech/phrase_hints.py` owns deterministic bounded command hints.
`core/assistant_runtime.py` remains the authority for command confidence,
rescue, confirmation, retry, refusal, dispatcher, and resolver flow. Parser and
post-processing remain safety gates, not bypassed execution shortcuts.

## Complexity Tracking

No constitution violations are expected for this feature. The design remains
incremental, adapter-oriented, command-mode scoped, opt-in by default,
rollback-friendly, non-visual, and measurable through existing tests and
runtime diagnostics.
