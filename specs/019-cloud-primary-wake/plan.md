# Implementation Plan: Cloud-Primary Wake Recognition and Standby Fallback Reliability

**Branch**: `[021-cloud-primary-wake]` | **Date**: 2026-04-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/019-cloud-primary-wake/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Keep it
aligned with `.specify/memory/constitution.md`.

## Summary

Make speech-based standby wake cloud-primary when rollout is explicitly enabled
by reusing the Phase 17 Google Cloud STT boundary, adding wake-specific phrase
hints and strict Vosk wake grammar fallback, and preserving existing keyword
and hardware-trigger wake paths.

The implementation stays incremental: `core/speech/legacy_wake.py` and
`core/stt.py` own bounded wake capture and recognition ordering,
`core/assistant_runtime.py` remains the authority for standby state
transitions and wake-only handling, `core/speech/provider_resolver.py` keeps
speech wake viable during weak-network conditions when strict local fallback is
still available, and `core/wake_word.py` remains the final canonical wake gate.

## Technical Context

**Language/Version**: Python 3.12.4  
**Primary Dependencies**: Existing runtime stack (`SpeechRecognition`, `rapidfuzz`, `edge-tts`, `playsound`, `customtkinter`), optional Google Cloud Speech boundary in `core/speech/google_cloud_stt.py`, Vosk strict fallback when installed, deterministic hint generation in `core/speech/phrase_hints.py`, wake scoring in `core/wake_word.py`, and `pytest`/`ruff` validation  
**Storage**: No new persisted datastore; `settings/user_profile.json` remains settings-only, rollout controls stay environment/config driven, standby wake attempt state stays in-memory, and diagnostics remain field-safe metadata with no raw utterance retention by default  
**Testing**: `pytest` unit coverage for wake alias/hint governance, cloud wake
ordering, strict wake fallback, non-canonical rejection, wake-plus-command
handling, provider-resolver network degradation, and telemetry contracts;
integration coverage for `AssistantRuntime` standby wake flow, repeated-miss
stability, and headless diagnostics; `ruff check .` and optional
`python -m compileall core tests` remain part of the validation path  
**Target Platform**: Windows desktop debug app and headless console runtime as
the wearable-reference execution path, while preserving weak-network and
non-visual standby behavior  
**Project Type**: Python voice assistant with runtime-first speech adapters, canonical wake scoring, and assistive wearable constraints  
**Performance Goals**: With cloud available, accept at least 95% of canonical
wake fixtures within the wake listening window (<= 7 seconds); with cloud
unavailable and strict local fallback enabled, accept at least 90% of the same
fixtures within the same window; produce zero false accepts across covered
negative wake fixtures; survive at least 50 consecutive wake misses without
stalling; emit a field-safe structured outcome for 100% of covered wake
attempts  
**Constraints**: No rewrite; keep wake logic out of `ui/`; preserve
`WAKE_MODE_KEYWORD_LOW_POWER`, `WAKE_MODE_HARDWARE_TRIGGER`, and
`WAKE_MODE_STT_BASED`; do not require always-on cloud streaming; do not accept
wake directly from raw transcripts without canonical matching; do not execute
or queue command text from a wake-plus-command utterance; network loss must
still allow strict local wake fallback when configured; keep default
diagnostics free of raw utterances and credentials  
**Scale/Scope**: Expected implementation changes in `core/assistant_runtime.py`,
`core/speech/legacy_wake.py`, `core/stt.py`, `core/speech/phrase_hints.py`,
`core/wake_word.py`, and `core/speech/provider_resolver.py`, with shared wake
status/failure labels extended only if needed in existing runtime models or
diagnostics; validation stays under `tests/unit/` and `tests/integration/`,
and `docs/STTInfo.md` may need rollout or wake-surface updates

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check

- [x] Incremental change: the plan extends the existing standby wake, STT,
      wake-word, provider-resolution, and diagnostics layers without replacing
      the runtime state machine or adding a new top-level package.
- [x] Runtime/UI separation: wake orchestration, fallback ordering, canonical
      acceptance, and telemetry stay in `core/` and `core/speech/`, not `ui/`.
- [x] Interface boundaries: Google Cloud STT and strict Vosk wake grammar stay
      behind the existing listener and wake-service boundaries with explicit
      timeout, no-match, and degraded behavior.
- [x] Structured results: speech wake planning defines machine-readable wake
      recognition, fallback, and standby outcome payloads that extend
      `spoken_text`, `status`, `payload`, `error_code`, source classification,
      and fallback markers.
- [x] Quality gates: automated tests, structured logging, wake fixtures,
      repeated-miss stability checks, and measurable wake timing targets are
      included in scope.

### Post-Design Re-Check

- [x] Phase 0 research resolves wake recognition ordering, network-down
      selection semantics, wake hint bounds, wake-plus-command handling, and
      telemetry/privacy boundaries without open clarifications.
- [x] Data model defines the approved wake alias catalog, wake hint set, wake
      recognition attempt/candidate, strict fallback outcome, fallback
      decision, and standby wake outcome.
- [x] Contracts define machine-readable wake recognition, hint, strict
      fallback, and standby outcome payloads used by runtime logic and tests.
- [x] Quickstart defines repeatable validation for disabled rollout parity,
      cloud wake success, cloud timeout-to-fallback success, non-canonical
      rejection, wake-plus-command safety, repeated misses, and field-safe
      diagnostics.
- [x] No constitution violations require Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/019-cloud-primary-wake/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- wake-recognition-result-contract.md
|   |-- wake-phrase-hints-contract.md
|   |-- strict-wake-fallback-contract.md
|   `-- standby-wake-outcome-contract.md
`-- tasks.md
```

### Source Code (repository root)

```text
main.py
controllers/
core/
|-- assistant_runtime.py
|-- stt.py
|-- wake_word.py
|-- speech/
|   |-- google_cloud_stt.py
|   |-- legacy_wake.py
|   |-- phrase_hints.py
|   `-- provider_resolver.py
settings/
tts/
ui/
tests/
|-- unit/
`-- integration/
docs/
```

**Structure Decision**: Keep Phase 19 inside the existing runtime-first wake
and speech layers. `core/assistant_runtime.py` remains the standby-loop and
state-transition authority, `core/speech/legacy_wake.py` owns wake capture
orchestration across keyword, hardware, and STT wake paths, `core/stt.py`
provides bounded cloud-primary plus strict-local speech wake recognition,
`core/speech/phrase_hints.py` owns deterministic wake hint and grammar
inventories, `core/wake_word.py` remains the canonical wake gate, and
`core/speech/provider_resolver.py` decides when STT-based wake remains viable
through strict local fallback during weak-network conditions. No new top-level
package is justified.

## Complexity Tracking

No constitution violations are expected for this feature. The design remains
incremental, runtime-first, adapter-oriented, opt-in by default, accessibility
safe, and measurable through existing diagnostics and tests.
