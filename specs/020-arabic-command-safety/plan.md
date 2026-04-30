# Implementation Plan: Arabic, Bilingual Canonicalization, and Safety Confidence Hardening

**Branch**: `[022-arabic-command-safety]` | **Date**: 2026-04-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/020-arabic-command-safety/spec.md`

**Note**: This plan was refreshed by `/speckit.plan` after the 2026-04-26
clarification session. It keeps the existing Phase 20 design artifacts aligned
with the current spec.

## Summary

Strengthen command understanding for supported Arabic, Egyptian-Arabic,
Arabizi, and mixed-language utterances by hardening deterministic transcript
canonicalization, classifying corrupted Arabic-like text before it reaches the
parser, and routing richer recognition metadata into the existing confidence,
retry, confirmation, and refusal policy.

The implementation remains incremental. `core/command_post_processing.py` owns
bounded normalization and curated variant mapping, `core/text_integrity.py`
remains the authority for mojibake and Unicode trust checks, `core/parser.py`
keeps command scope tied to existing intent IDs, `core/assistant_runtime.py`
stays responsible for confidence-band decisions and runtime recovery, and
`core/dialog_policy.py` plus `core/closed_vocabulary.py` preserve safe
multilingual confirmation behavior.

## Technical Context

**Language/Version**: Python 3.12.4  
**Primary Dependencies**: Existing runtime stack (`SpeechRecognition`,
`rapidfuzz`, `edge-tts`, `playsound`, `customtkinter`), optional Google Cloud
STT boundary in `core/speech/google_cloud_stt.py`, strict Vosk fallback in
`core/stt.py`, deterministic command post-processing in
`core/command_post_processing.py`, integrity checks in
`core/text_integrity.py`, dialog safety helpers in `core/dialog_policy.py`,
and `pytest`/`ruff` validation  
**Storage**: No new persisted datastore; `settings/user_profile.json` remains
settings-only, curated supported-variant inventories stay repo-hosted in code
and fixtures, and command-safety diagnostics remain field-safe metadata with
no raw utterance retention by default  
**Testing**: `pytest` unit coverage for normalization, integrity rejection,
parser inventory expansion, confidence-policy branching, confirmation dialog
parity, and contract validation; integration coverage for runtime command
recognition, protected-command safety, language mismatch recovery, and
privacy-safe diagnostics; `ruff check .` plus optional
`python -m compileall core tests` stay in the validation path  
**Target Platform**: Windows desktop debug app and headless console runtime as
the wearable-reference execution path, with non-visual command recovery kept
consistent across weak-network and fallback recognition conditions  
**Project Type**: Python voice assistant with runtime-first speech adapters,
deterministic command canonicalization, and safety-gated command execution  
**Performance Goals**: Resolve at least 95% of covered supported Arabic
command fixtures to the intended existing command identifier; resolve at least
90% of covered bilingual and phonetic fixtures without requiring more than one
retry; allow zero protected-command executions without explicit affirmative
confirmation under ambiguity or corruption; reject 100% of covered corrupted
Arabic-like and mojibake fixtures safely; emit field-safe decision metadata
for 100% of covered command outcomes that rely on major normalization,
ambiguity, or language mismatch  
**Constraints**: No rewrite; keep authoritative logic out of `ui/`; do not
introduce an open-domain language model; do not widen executable command scope
beyond the existing catalog; do not learn new executable variants from field
utterances by default; corrupted Arabic-like or mojibake text must stay
non-executable; medium-risk mismatch cases confirm only when a stable
supported candidate survives; protected commands remain under strict explicit
confirmation; default diagnostics must stay metadata-only and field-safe  
**Scale/Scope**: Expected implementation changes in
`core/command_post_processing.py`, `core/parser.py`,
`core/assistant_runtime.py`, `core/dialog_policy.py`,
`core/closed_vocabulary.py`, and `core/text_integrity.py`, with supporting
test and documentation updates in `tests/unit/`, `tests/integration/`,
`tests/smoke/`, and `docs/STTInfo.md` if command-recognition behavior or
diagnostics guidance changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check

- [x] Incremental change: the plan extends the existing command
      post-processing, parser, runtime-decision, and dialog layers without
      replacing the command pipeline or adding a new top-level package.
- [x] Runtime/UI separation: command canonicalization, integrity gating,
      confidence policy, and confirmation handling remain in `core/` and do
      not shift long-term authority into `ui/`.
- [x] Interface boundaries: recognition output continues to flow through the
      existing post-processing, parser, and runtime contracts rather than
      bypassing adapters or hard-wiring provider-specific logic into command
      execution.
- [x] Structured results: the design extends machine-readable
      post-processing, safety-decision, confirmation, and diagnostics payloads
      so `spoken_text`, `status`, `payload`, and `error_code` remain explicit
      where capability results are involved.
- [x] Quality gates: automated tests, structured diagnostics, smoke
      validation, and measurable accuracy/safety targets are included in
      scope.

### Post-Design Re-Check

- [x] Phase 0 research resolves supported-variant governance, corruption
      policy, confirmation triggers, and field-safe metadata boundaries
      without leaving open clarification items.
- [x] Data model defines the curated variant mapping rule, text integrity
      assessment, normalized command candidate, confidence evidence, safety
      decision record, and confirmation dialog turn used by runtime logic and
      tests.
- [x] Contracts define machine-readable post-processing, variant-mapping,
      command-safety, and confirmation payloads appropriate for the current
      runtime architecture.
- [x] Quickstart defines repeatable validation for supported Arabic and mixed
      commands, corrupted-text rejection, language mismatch recovery,
      protected-command confirmation, and field-safe diagnostics.
- [x] No constitution violations require Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/020-arabic-command-safety/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- confirmation-dialog-safety-contract.md
|   |-- normalized-command-candidate-contract.md
|   |-- safety-decision-record-contract.md
|   `-- variant-mapping-rule-contract.md
`-- tasks.md
```

### Source Code (repository root)

```text
main.py
controllers/
core/
|-- assistant_runtime.py
|-- closed_vocabulary.py
|-- command_models.py
|-- command_post_processing.py
|-- dialog_policy.py
|-- parser.py
|-- text_integrity.py
|-- speech/
|   |-- google_cloud_stt.py
|   |-- phrase_hints.py
|   `-- provider_resolver.py
settings/
tts/
ui/
tests/
|-- unit/
|-- integration/
`-- smoke/
docs/
```

**Structure Decision**: Keep Phase 20 inside the existing runtime-first
command pipeline. `core/command_post_processing.py` remains the canonical
normalization surface for parser-ready text, `core/text_integrity.py` stays
the shared trust gate for corrupted Unicode paths, `core/parser.py` continues
to own intent matching against the supported command catalog,
`core/assistant_runtime.py` remains the authority for confidence-driven
execution, retry, confirmation, and refusal outcomes, and
`core/dialog_policy.py` plus `core/closed_vocabulary.py` preserve multilingual
safe-confirmation behavior. No new top-level package is justified.

## Complexity Tracking

No constitution violations are expected for this feature. The design remains
incremental, runtime-first, adapter-oriented, safety-gated, and measurable
through existing diagnostics and tests.
