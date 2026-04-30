# Research: Cloud-Primary Wake Recognition and Standby Fallback Reliability

## Decision: Reuse the Phase 17 Google Cloud STT boundary and Phase 18 strict Vosk plumbing for wake

- **Decision**: Use `core/speech/google_cloud_stt.py` as the only cloud wake
  recognizer and reuse the existing strict local Vosk path in `core/stt.py`
  for `standby_wake` rather than introducing a separate wake-only provider
  stack.
- **Rationale**: The project already has optional cloud availability checks,
  bounded timeout handling, failure reason codes, and deterministic hint
  infrastructure. Reusing those boundaries keeps provider-specific behavior out
  of `AssistantRuntime` and preserves the replaceable speech-interface
  principle from the constitution.
- **Alternatives considered**:
  - Add a second wake-only cloud client: rejected because it duplicates
    credentials, timeout mapping, and privacy logic.
  - Keep wake on raw `recognize_google()` or PocketSphinx compatibility paths:
    rejected because the phase requires bounded, structured, production-ready
    wake recognition and no default PocketSphinx wake decisions.

## Decision: Route STT-based wake through a bounded structured `standby_wake` capture path

- **Decision**: For `WAKE_MODE_STT_BASED`, use wake-specific structured
  capture with `usage_mode="standby_wake"` and
  `capture_profile_id="standby_wake.default"` instead of relying on broad
  `listen_any(...)` free-form behavior as the long-term authority.
- **Rationale**: Wake needs stricter timing, deterministic fallback ordering,
  and machine-readable source metadata than the current free-form standby
  listen path provides. A structured wake path also aligns with the existing
  audio capture profile system and the Phase 19 7-second wake window.
- **Alternatives considered**:
  - Leave STT wake on `listen_any(...)` and post-filter the text:
    rejected because it makes cloud/fallback ordering, source metadata, and
    wake-only safeguards harder to enforce consistently.
  - Move standby ownership out of `AssistantRuntime`: rejected because the
    runtime already owns wake state transitions and should stay authoritative.

## Decision: Keep canonical wake evaluation as the only acceptance authority, and treat wake-plus-command as wake-only

- **Decision**: Continue using `detect_wake(...)` and
  `is_canonical_wake_phrase(...)` as the final acceptance gates, even when
  cloud or strict local STT produces a high-confidence transcript. When the
  transcript contains a canonical wake phrase plus extra command text, accept
  the wake only and explicitly drop the command content from that utterance.
- **Rationale**: The spec requires wake acceptance to stay canonical and
  safety-gated, while also allowing natural speech such as "hi egb open
  navigation" to wake the assistant without immediately executing the command.
- **Alternatives considered**:
  - Accept high-confidence cloud transcripts directly: rejected because that
    would bypass the existing canonical wake rules.
  - Reject every wake-plus-command utterance: rejected because it worsens the
    non-visual interaction flow and is stricter than the clarified behavior.

## Decision: Preserve STT-based wake during cloud or network loss when strict local wake fallback is still available

- **Decision**: Update wake selection and availability logic so STT-based wake
  is not considered unavailable purely because cloud is offline, as long as
  strict local wake fallback remains configured and usable.
- **Rationale**: The current provider-resolution logic ties STT wake
  availability to network availability. Phase 19 explicitly requires
  cloud-failure and network-down cases to continue through strict local wake
  fallback where allowed.
- **Alternatives considered**:
  - Treat all network loss as STT wake unavailable: rejected because it would
    incorrectly degrade standby even when the local strict wake grammar can
    still run.
  - Ignore network state entirely: rejected because cloud-primary attempts
    still need truthful failure reporting and bounded degraded behavior.

## Decision: Build a bounded deterministic wake hint and strict grammar inventory from the approved alias catalog

- **Decision**: Generate wake hints and strict grammar phrases only from the
  approved wake alias catalog in `core/wake_word.py`, with recommended caps of
  `24` cloud hint phrases and `32` strict grammar phrases after normalization
  and deduplication.
- **Rationale**: Wake recognition needs enough bilingual and phonetic coverage
  to reduce false rejects, but an overgrown hint inventory increases false
  wake risk and becomes harder to audit. Using the approved alias catalog keeps
  hints deterministic, privacy-safe, and aligned with canonical acceptance.
- **Alternatives considered**:
  - Reuse the full command hint inventory for wake: rejected because wake and
    command contexts have different safety requirements.
  - Learn wake variants from captured field transcripts: rejected because the
    default system must remain field-safe and avoid raw utterance retention.

## Decision: Emit a field-safe wake outcome taxonomy that distinguishes accepted, rejected, missed, and fallback-used attempts

- **Decision**: Extend the existing standby wake outcome and diagnostics so
  wake attempts explicitly distinguish at least `wake_accepted`,
  `wake_rejected`, `wake_missed`, `degraded_standby`, and the source
  classifications `cloud_primary`, `wake_strict_vosk_fallback`, and
  `noncanonical_rejected`, without storing raw transcripts by default.
- **Rationale**: Release owners need to measure whether cloud wake actually
  improves wearable reliability, and the spec requires that cloud failure,
  fallback usage, and non-canonical rejections remain distinguishable without
  persisting user speech.
- **Alternatives considered**:
  - Keep plain-text logs only: rejected because reliability review needs
    structured assertions.
  - Persist raw wake transcripts for easier debugging: rejected because it
    violates the privacy boundary in the spec and prior STT phases.

## Decision: Validate the feature through deterministic fake cloud outcomes, negative wake fixtures, and repeated-miss stability runs

- **Decision**: Use fake or monkeypatched cloud responses for automated tests,
  reuse the bilingual wake fixture style already present in the repo, and add
  repeated-miss stability coverage for at least 50 consecutive standby wake
  misses.
- **Rationale**: Wake reliability regressions need repeatable evidence without
  live Google credentials or field audio capture, and the spec calls out both
  confusion fixtures and repeated-miss stability as mandatory validation.
- **Alternatives considered**:
  - Require live cloud credentials in the default test suite: rejected because
    it makes local and CI validation fragile.
  - Limit validation to happy-path canonical wake phrases: rejected because the
    feature is mainly about safe fallback and false-trigger control.
