# Research: Hybrid Command Recognition and Post-Processing

## Decision: Extend recognition into a structured command-recognition result contract

- **Decision**: The STT boundary should return a structured command-recognition
  result containing the primary transcript, optional confidence score,
  alternative transcripts when available, recognition-path metadata, and basic
  latency data instead of returning only a raw string.
- **Rationale**: Phase 13 requires confidence-aware fallback and telemetry, and
  the existing `VoiceListener` string-only return shape is too narrow for safe
  escalation decisions. Extending the contract is the smallest change that
  keeps the current listener and runtime flow recognizable while unlocking
  richer decision logic.
- **Alternatives considered**:
  - Keep raw-string STT output and infer confidence elsewhere: rejected because
    runtime safety decisions would become fragile and inconsistent.
  - Replace the whole command pipeline with a new recognizer abstraction:
    rejected because it would violate the incremental-change principle.

## Decision: Keep recognition local-first and trigger fallback only on uncertainty

- **Decision**: The runtime should always try the fast local recognition path
  first, then invoke a stronger fallback recognizer only when confidence is
  below the execution threshold or when alternatives leave intent resolution
  ambiguous.
- **Rationale**: The wearable experience depends on responsiveness, and the
  spec explicitly targets fallback only when needed. This preserves low-latency
  behavior for ordinary commands while still improving accuracy under noisy or
  ambiguous conditions.
- **Alternatives considered**:
  - Always run both recognizers: rejected because it adds avoidable latency and
    complexity to every command.
  - Prefer fallback as the default path: rejected because it weakens offline
    safety and local responsiveness.

## Decision: Treat missing confidence as uncertain instead of optimistic

- **Decision**: Recognition results without a usable confidence score should be
  treated as uncertain by default, allowing immediate execution only when
  post-processing leaves a single supported non-protected interpretation.
- **Rationale**: The clarification pass already established this rule, and it
  is the safest way to support legacy or limited recognizers without granting
  them silent execution authority over risky commands.
- **Alternatives considered**:
  - Treat missing confidence as high confidence: rejected because it creates a
    silent unsafe path.
  - Reject all no-confidence results immediately: rejected because it would
    unnecessarily block clear low-risk local commands.

## Decision: Introduce a dedicated command post-processing layer before parsing

- **Decision**: Transcript normalization, common Arabic and English STT
  substitutions, and command phrase canonicalization should live in a dedicated
  post-processing module that runs before `core.parser.parse_command`.
- **Rationale**: The current parser keyword list is already large, and Phase 13
  adds bilingual correction logic that is easier to reason about as a
  pre-parser transformation stage than as more keyword sprawl. This keeps the
  parser focused on intent matching rather than transcript repair.
- **Alternatives considered**:
  - Keep adding STT variations directly to parser keywords: rejected because it
    scales poorly and mixes recognition repair with intent rules.
  - Perform normalization in the GUI or UI bridge: rejected because command
    meaning must stay runtime-owned.

## Decision: Reuse existing confirmation and clarification flows, but make them confidence-aware

- **Decision**: Existing resolver and runtime confirmation or clarification
  surfaces should remain the authority for protected-command approval and
  bounded retry, but they should now be triggered from explicit confidence
  bands rather than parser thresholds alone.
- **Rationale**: The repo already has protected-command and clarification logic,
  including bounded retries. Reusing those paths keeps behavior consistent and
  avoids duplicating safety dialogs in the new recognition flow.
- **Alternatives considered**:
  - Build a second standalone confirmation engine for STT uncertainty:
    rejected because it would fragment dialog behavior.
  - Skip confirmation once fallback proposes a plausible transcript: rejected
    because protected commands must remain explicitly affirmed.

## Decision: Keep threshold and fallback policy runtime-configurable through settings

- **Decision**: Confidence thresholds, fallback enablement, and related
  command-recognition policy should be surfaced through the existing settings
  boundary and runtime snapshots rather than through ad hoc constants spread
  across runtime modules.
- **Rationale**: `settings/settings_manager.py` is already the authority for
  runtime configuration, provider selection, wake behavior, and other wearable
  policy values. Keeping command-recognition policy there preserves the current
  architecture and makes tests and runtime snapshots easier to reason about.
- **Alternatives considered**:
  - Hard-code thresholds inside `assistant_runtime.py`: rejected because it
    hides operational policy and complicates test setup.
  - Create a separate top-level configuration system: rejected because the repo
    already has a central settings authority.

## Decision: Record metadata-first recognition telemetry

- **Decision**: Command-recognition telemetry should record session identifier,
  recognition path, confidence band, fallback usage, decision outcome,
  protected-command flag, and latency impact, while excluding raw utterances
  from the default artifact set.
- **Rationale**: The spec requires measurable fallback usage and latency impact,
  but privacy-aware diagnostics are already a project standard. Metadata-first
  telemetry supports triage and release review without broad content capture.
- **Alternatives considered**:
  - Store raw utterances in all telemetry: rejected because it expands data
    exposure beyond the Phase 13 need.
  - Skip telemetry entirely and rely on tests only: rejected because runtime
    behavior needs observability in real sessions.

## Decision: Validate the feature across noisy, bilingual, offline, and safety-critical flows

- **Decision**: Phase 13 validation should combine unit tests for normalization
  and confidence policy, integration tests for runtime fallback and protected
  commands, and smoke tests that prove the local-first command path remains
  usable and bounded.
- **Rationale**: The feature cuts across STT, runtime orchestration, parsing,
  resolution, and settings. One test layer alone would miss regressions in
  either the transformation rules or the end-to-end behavior.
- **Alternatives considered**:
  - Unit tests only: rejected because fallback escalation and protected-command
    flows cross module boundaries.
  - Manual smoke validation only: rejected because confidence bands and
    bilingual normalization need regression protection.
