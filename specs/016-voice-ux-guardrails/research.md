# Research: Continuous Turn-Taking, Closed-Vocabulary Guardrails, and Pilot-Grade Voice UX

## Decision: Extract a small runtime-owned turn-taking coordinator instead of leaving prompt-window rules inline

- **Decision**: Introduce a focused `core/turn_taking.py` module that decides
  when a guided prompt is speaking-only, speaking-with-barge-in, actively
  listening, closed-vocabulary listening, waiting for confirmation, or
  recovering after no-input or clipped input.
- **Rationale**: `core/assistant_runtime.py` already contains onboarding and
  prompt-echo behavior. Phase 16 needs that behavior made consistent and
  reusable, not replaced by a second runtime loop.
- **Alternatives considered**:
  - Keep all turn-taking logic embedded in `core/assistant_runtime.py`:
    rejected because barge-in rules, retry windows, and protected-flow
    boundaries would stay hard to reason about and test.
  - Build a separate dialog runtime service: rejected because it would split
    runtime authority and violate the project's incremental design principle.

## Decision: Use a declarative closed-vocabulary registry shared by STT, runtime, and resolver layers

- **Decision**: Define guided answer sets in a shared registry module such as
  `core/closed_vocabulary.py`, keyed by stable `closed_vocabulary_id` values
  that can be consumed by STT filtering, runtime validation, and resolver-safe
  follow-up handling.
- **Rationale**: The current code already carries `closed_vocabulary_id` and
  `dictionary_bias_mode` through structured speech models. A shared registry
  turns those IDs into a single source of truth instead of scattered phrase
  lists.
- **Alternatives considered**:
  - Keep alias lists in multiple modules: rejected because it would create
    drift between recognition, runtime prompts, and dialog resolution.
  - Treat guided responses as open dictation with fuzzy interpretation:
    rejected because the feature specifically needs stronger guardrails and
    explicit out-of-domain rejection.

## Decision: Reuse the existing prompt catalog and add shorter retry variants rather than embedding prompt text in control logic

- **Decision**: Keep `core/critical_prompts.py` and the profile-backed prompt
  catalog as the source of truth for onboarding, clarification, confirmation,
  and retry prompts, extending prompt surfaces only where Phase 16 needs
  shorter or narrower wording.
- **Rationale**: The repository already protects critical spoken text through a
  catalog and integrity checks. Reusing that path preserves localization and
  safety guarantees.
- **Alternatives considered**:
  - Hard-code retry text inside runtime helpers: rejected because it would
    bypass catalog integrity and increase localization drift.
  - Create a second prompt store just for guided dialogs: rejected because it
    would duplicate an existing capability without adding value.

## Decision: Limit preemption of closed-vocabulary turns to approved global safety commands

- **Decision**: While a guided flow is waiting for a closed-choice answer,
  unrelated non-safety commands remain inside the current context; only the
  approved global safety vocabulary or an existing higher-priority safety rule
  may interrupt the flow.
- **Rationale**: This matches the clarification outcome and prevents settings
  and onboarding flows from being derailed by opportunistic parser matches.
- **Alternatives considered**:
  - Let any recognized command escape the guided context: rejected because it
    would weaken the user's sense of progress and make recovery unpredictable.
  - Block every interruption unconditionally: rejected because the product
    already has global safety commands that must remain available.

## Decision: Use recent prompt text plus timing-aware token overlap for prompt-echo rejection

- **Decision**: Base prompt-echo suppression on recently spoken prompt text,
  token overlap, short-turn heuristics, and timing proximity to TTS playback,
  while allowing genuine short approved answers to pass.
- **Rationale**: The current runtime already applies a basic version of this
  logic. Extending it is lower risk than introducing audio fingerprinting or
  acoustic echo cancellation for a dialog-policy problem.
- **Alternatives considered**:
  - Depend on audio-level echo cancellation only: rejected because the bug the
    spec targets is often transcript overlap and timing, not only audio path
    leakage.
  - Ignore prompt echo and rely on retries: rejected because prompt echo is a
    direct cause of the confusing loops this phase exists to remove.

## Decision: Continue guided setup with safe defaults for required settings and discard unconfirmed personalization

- **Decision**: When retry limits are exhausted, required onboarding and
  settings choices keep the last confirmed or safe default value and continue
  if that remains safe, while unconfirmed personalization such as spoken names
  is discarded rather than persisted.
- **Rationale**: The clarified spec prefers graceful continuation over trapping
  users in loops, but still treats uncertain identity-like values more
  cautiously than language or speed defaults.
- **Alternatives considered**:
  - Always fail and exit after the final retry: rejected because it would make
    first-run setup brittle and frustrating.
  - Persist the most recent guess for every field: rejected because it would
    allow uncertain names and other weak inputs to become accepted state.

## Decision: Require explicit confirmation before any captured name becomes final

- **Decision**: Treat name capture as a candidate state that becomes accepted
  only after a clear affirmative confirmation; negative, cancel, or uncertain
  follow-ups discard the candidate.
- **Rationale**: The runtime already has protected confirmation vocabulary and
  name-confirm prompts. Using the same explicit-confirmation rule keeps the
  user's identity value from being finalized on noisy input.
- **Alternatives considered**:
  - Accept high-confidence names without confirmation: rejected because names
    are especially sensitive to clipping and prompt-echo artifacts.
  - Force repeated capture until a name is understood perfectly: rejected
    because it would create fragile loops for a personalization field that can
    be skipped safely.

## Decision: Record pilot-grade UX evidence through lightweight local artifacts without raw utterances by default

- **Decision**: Use structured local evidence for completion status, retries,
  accepted barge-ins, prompt-echo suppressions, out-of-domain rejections, and
  fallback or exit reasons, reusing the project's local artifact pattern rather
  than a mandatory external telemetry platform.
- **Rationale**: The team needs measurable pilot UX evidence, but the
  repository already favors field-safe local artifacts and avoids raw user
  utterances in default evidence.
- **Alternatives considered**:
  - Store raw user transcripts in default artifacts: rejected because the
    current privacy posture and earlier phases explicitly avoid that by
    default.
  - Depend on a hosted observability system: rejected because it would exceed
    the feature scope and deployment needs.
