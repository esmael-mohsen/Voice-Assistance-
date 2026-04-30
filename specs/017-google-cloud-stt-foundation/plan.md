# Implementation Plan: Google Cloud STT Foundation and Strict Fallback Contracts

**Branch**: `[018-google-cloud-stt-foundation]` | **Date**: 2026-04-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/017-google-cloud-stt-foundation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. Keep it
aligned with `.specify/memory/constitution.md`.

## Summary

Introduce a production-grade, optional Google Cloud Speech-to-Text foundation
inside the existing provider-aware STT architecture, while keeping runtime
entry points stable, generating deterministic phrase hints, converting Vosk
fallback into strict grammar-constrained modes, and removing PocketSphinx from
default wake and command accuracy decisions unless compatibility is explicitly
enabled.

## Technical Context

**Language/Version**: Python 3.12.4  
**Primary Dependencies**: Existing runtime stack (`SpeechRecognition`,
`rapidfuzz`, `edge-tts`, `playsound`, `customtkinter`, Vosk integration when
installed) plus optional official Google Cloud Speech client dependency
`google-cloud-speech` for `google.cloud.speech_v2.SpeechClient`,
`google-api-core` exception/retry types supplied by the Google client,
`pytest` for unit and integration validation, and `ruff`/`compileall` for local
quality checks  
**Storage**: Existing local JSON profile at `settings/user_profile.json` for
runtime settings continuity only; Google credential material stays outside the
profile and is read from normal environment/application-default credential
locations; deterministic phrase hints are generated from repository catalogs;
field-safe diagnostics and release artifacts avoid raw utterances and cloud
credentials by default  
**Testing**: `pytest` unit coverage with fake Google client responses and fake
Vosk recognizer payloads; integration coverage for `VoiceListener` candidate
ordering, `LegacySpeechToTextAdapter` compatibility, provider availability
metadata, feature flags, no-credential startup, strict fallback no-match, and
PocketSphinx compatibility gating; smoke validation in headless runtime mode;
`python -m compileall core tests` and `python -m ruff check .` remain part of
the validation path  
**Target Platform**: Windows desktop debug app and headless console runtime as
the reference validation paths, with Raspberry Pi 4 Model B/wearable deployment
constraints preserved for offline degradation and bounded latency  
**Project Type**: Python voice assistant with provider-aware speech adapters,
runtime-first orchestration, bilingual assistive command recognition, strict
fallback contracts, and debug GUI parity  
**Performance Goals**: Default cloud recognition attempt is bounded to 3
seconds with at most one transient retry inside the existing listen window;
startup and tests complete 100% of the time without Google credentials; strict
wake, command, confirmation, and closed-choice grammars are deterministic
across repeated runs; default production wake and command candidate lists
contain zero PocketSphinx candidates unless compatibility is explicitly
enabled; no cloud credentials or raw utterances appear in profile/log/artifact
validation  
**Constraints**: Preserve `AssistantRuntime`, parser, dispatcher, resolver,
provider IDs (`legacy`, `speakkit`), and public listener methods; keep Google
client import optional so local development and CI do not require cloud
credentials; use cloud-primary behavior only when explicitly enabled; keep
strict Vosk fallback independently configurable; when cloud fails and strict
Vosk fallback is disabled, return no usable transcript and let existing
recovery handle the turn; treat detected cloud language as metadata only; do
not add an LLM, external telemetry platform, or new top-level runtime package  
**Scale/Scope**: Add `core/speech/google_cloud_stt.py` and
`core/speech/phrase_hints.py`; adjust `core/stt.py` candidate ordering,
strict-Vosk modes, PocketSphinx gating, feature-flag reading, source metadata,
and `CommandRecognitionResult` population without changing public method names;
extend `core/speech/interfaces.py`, `core/speech/legacy_stt.py`, and
`core/speech/provider_registry.py` only as needed for typed candidate/availability
contracts; update release artifact serialization only where needed to preserve
field-safe STT diagnostics in `core/release_artifacts.py` and
`core/release_models.py`; update `requirements.txt`, `docs/STTInfo.md`, and
tests under `tests/unit/` and `tests/integration/`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check

- [x] Incremental change: the plan adds a Google Cloud STT boundary and strict
      fallback contracts inside existing STT/provider modules without replacing
      `AssistantRuntime`, parser, dispatcher, resolver, or provider IDs.
- [x] Runtime/UI separation: provider selection, recognition ordering, phrase
      hints, fallback contracts, and diagnostics remain in `core/`,
      `core/speech/`, `settings/`, `docs/`, and `tests/`, not in `ui/`.
- [x] Interface boundaries: the cloud recognizer is introduced behind a
      dedicated speech adapter boundary with credential checks, timeout,
      retry, failure codes, and fallback behavior before production use.
- [x] Structured results: cloud candidates, strict fallback outcomes,
      phrase-hint sets, provider availability, and diagnostic decisions are
      machine-readable and feed the existing `CommandRecognitionResult`
      contract.
- [x] Quality gates: the plan includes fake-client tests, no-credential startup
      validation, deterministic grammar tests, PocketSphinx gating tests,
      field-safe diagnostics checks, smoke validation, and bounded latency
      targets.

### Post-Design Re-Check

- [x] Phase 0 research resolves the cloud client boundary, optional import and
      credentials strategy, feature-flag defaults, phrase-hint generation,
      strict Vosk fallback semantics, PocketSphinx deactivation, language
      metadata handling, and privacy boundaries.
- [x] Data model defines cloud candidates, provider availability, failure
      reason codes, phrase-hint sets, fallback grammar contracts, recognition
      configuration, language metadata, and diagnostic events with validation
      rules.
- [x] Contracts define the cloud candidate/failure shape, deterministic phrase
      hint shape, strict Vosk fallback shape, and effective recognition
      configuration shape consumed by tests and runtime integration.
- [x] Quickstart defines repeatable validation for disabled cloud defaults,
      fake cloud responses, failure classification, strict Vosk no-match,
      PocketSphinx gating, language metadata, privacy, and docs checks.
- [x] No constitution violations require Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/017-google-cloud-stt-foundation/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- cloud-stt-candidate-contract.md
|   |-- phrase-hints-contract.md
|   |-- strict-vosk-fallback-contract.md
|   `-- recognition-configuration-contract.md
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
|-- unit/
|-- integration/
docs/
```

**Structure Decision**: Keep Phase 17 within the existing runtime and provider
layout. `core/stt.py` remains the legacy listener and public listening method
surface, while `core/speech/google_cloud_stt.py` owns Google client creation,
credential availability checks, short-utterance recognition, timeout/retry
mapping, and structured candidate extraction. `core/speech/phrase_hints.py`
owns deterministic phrase sets built from `core.parser.COMMAND_CATALOG`,
`core.closed_vocabulary`, canonical wake aliases, curated assistive phrases,
and safety-critical terms. `core/stt.py` consumes those helpers for cloud-first
recognition when enabled, strict Vosk fallback modes, and PocketSphinx
compatibility gating. Provider metadata remains in `core/speech/interfaces.py`,
`core/speech/legacy_stt.py`, and `core/speech/provider_registry.py`. Docs stay
in `docs/STTInfo.md`, and validation stays under `tests/` with fake clients so
CI does not require Google credentials.

## Complexity Tracking

No constitution violations are expected for this feature. The design remains
incremental, runtime-first, adapter-oriented, accessibility-safe, optional by
configuration, rollback-friendly, and measurable through the existing
repository layout.
