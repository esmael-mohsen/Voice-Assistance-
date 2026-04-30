# Research: Cloud-Primary Command Recognition and Safety-Aware Fallback

## Decision: Reuse the Phase 17 Google Cloud STT boundary

**Rationale**: Phase 17 already introduced optional Google Cloud STT candidate
extraction, availability checks, timeout/failure codes, phrase hints, and
field-safe metadata. Reusing that boundary keeps provider-specific behavior out
of command policy and satisfies the replaceable speech-interface constitution
principle.

**Alternatives considered**:
- Add a second command-only Google client: rejected because it duplicates
  credential handling, timeout mapping, and privacy protections.
- Route commands through generic SpeechRecognition cloud fallback: rejected
  because it does not expose the structured metadata and deterministic phrase
  hint controls required by this phase.

## Decision: Make command recognition cloud-primary only when explicitly enabled

**Rationale**: Opt-in rollout preserves current command behavior for existing
users and gives release owners a rollback path. Disabled cloud-primary behavior
must exercise the same local-compatible path and regression fixtures as before.

**Alternatives considered**:
- Enable cloud-primary by default: rejected because the foundation is optional
  and may not have credentials, network, or quota in local and wearable runs.
- Add a separate persisted profile setting immediately: rejected because Phase
  17 already uses environment/config controls and the spec requires no new
  datastore.

## Decision: Keep command execution authority in existing runtime policy

**Rationale**: Cloud recognition improves candidate quality, but execution must
still pass post-processing, parser validation, confidence policy, dispatcher,
resolver, and protected-command confirmation. Provider confidence is an input
to the existing thresholds, not a new execution shortcut.

**Alternatives considered**:
- Execute high-confidence cloud transcripts directly: rejected because it would
  bypass protected-command confirmation and parser safety.
- Introduce separate cloud-specific confidence thresholds: rejected because it
  would create competing safety rules and complicate regression expectations.

## Decision: Split fallback trigger ownership by failure type

**Rationale**: Provider-level failures are best handled in `core/stt.py` before
returning a successful command result, while semantic and safety-level failures
are best handled in `AssistantRuntime` after post-processing and parser
evaluation.

Provider-level triggers handled by listener ordering:
- Cloud timeout
- Cloud unavailable
- Cloud empty result
- Missing transcript

Runtime policy triggers handled after candidate evaluation:
- Low or borderline confidence
- Language mismatch penalty
- Alternatives conflict
- Endpoint clipping hints
- No command-like structure
- Parser or post-processing rejection

When runtime policy requests rescue or fallback, the listener should use the
same bounded command window and strict command grammar fallback when enabled.

**Alternatives considered**:
- Force all fallback decisions inside `core/stt.py`: rejected because parser
  and protected-command context are not fully known there.
- Force all fallback decisions inside `AssistantRuntime`: rejected because
  timeout, empty, and provider-unavailable cases can be safely resolved before
  constructing a successful command candidate.

## Decision: Use strict command grammar fallback, never broad local dictation

**Rationale**: Strict fallback must only promote phrases that map to the
approved command inventory or active closed vocabulary. No-match outcomes
return no usable transcript and let existing retry, confirmation, or safe
refusal behavior continue.

**Alternatives considered**:
- Fall back to unrestricted Vosk dictation: rejected because arbitrary text can
  look command-like after post-processing.
- Fall back to PocketSphinx in production command mode: rejected because Phase
  17 made PocketSphinx compatibility explicitly disabled by default.

## Decision: Govern command phrase hints with deterministic caps and priority

**Rationale**: Phrase hints should bias the cloud recognizer toward supported
assistive commands without expanding into open-ended dictation. The command
hint set should be stable, deduplicated, field-safe, and capped.

Recommended priority order:
1. Protected and safety-critical commands.
2. Parser catalog canonical keywords.
3. High-value assistive wearable commands.
4. Arabic variants.
5. Bilingual and phonetic variants.
6. Common STT mistake variants.

Recommended default caps:
- Cloud command phrase hints: 72 phrases by default, derived from the Phase 17
  default of `cloud_max_alternatives * 24`.
- Strict command grammar inventory: 220 phrases by default, aligned with the
  existing listener command grammar cap.

**Alternatives considered**:
- No cap: rejected because large hint sets become harder to audit and can
  reduce recognizer bias quality.
- Learn hints from raw user utterances: rejected because default behavior must
  avoid raw user content persistence.

## Decision: Treat wake wording as non-authoritative in command mode

**Rationale**: Users may say wake plus command in one phrase while already in
command mode. Wake tokens may be stripped or penalized during command
post-processing, but they must not raise confidence, bypass parser validation,
or bypass protected-command confirmation.

**Alternatives considered**:
- Reject every wake-plus-command phrase: rejected because it creates a poor
  non-visual user experience for natural speech.
- Treat wake wording as extra confirmation: rejected because wake phrases are
  not explicit authorization for protected actions.

## Decision: Keep diagnostics field-safe and useful for headless validation

**Rationale**: The assistant must be diagnosable without GUI inspection. Events
should expose recognition source, fallback decision, confidence band, language
mismatch, failure reason, latency category, and raw-content retention state.

**Alternatives considered**:
- Log raw transcripts for easier debugging: rejected because field diagnostics
  and release artifacts must not retain raw utterances by default.
- Hide source metadata from runtime events: rejected because it makes cloud vs
  strict fallback behavior hard to validate in headless runs.

## Decision: Validate with fake cloud responses and deterministic fixtures

**Rationale**: Tests should not require live Google credentials, network, or
quota. Fake cloud candidates can cover success, alternatives, low confidence,
timeouts, unavailable states, empty results, language mismatch, and failure
codes deterministically.

**Alternatives considered**:
- Require live Google Cloud integration tests in the default suite: rejected
  because it makes local and CI validation fragile.
- Validate only with manual microphone runs: rejected because regressions in
  safety and fallback behavior need repeatable automated coverage.
