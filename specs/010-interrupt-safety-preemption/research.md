# Research: Interrupt Safety and TTS Preemption

## Decision: Keep interrupt phrases as a global bilingual safety vocabulary

- **Decision**: Approved Arabic and English interrupt phrases should remain
  valid regardless of the current prompt language.
- **Rationale**: Safety commands need the lowest possible recall burden, and a
  global bilingual vocabulary reduces the chance that the user says the right
  stop phrase in the "wrong" active language during a stressful moment.
- **Alternatives considered**:
  - Restrict interrupts to the active language only: rejected because it adds
    avoidable failure risk for safety-critical speech control.
  - Let any loosely similar phrase count as an interrupt: rejected because
    overly broad matching would increase false interruption risk.

## Decision: Route interrupts through one runtime-owned detection and recovery path

- **Decision**: Interrupt recognition should stay owned by the runtime loop and
  produce one canonical recovery outcome path for accepted interrupts.
- **Rationale**: The current assistant already emits structured recovery events
  for interrupt handling, so Phase 10 should strengthen that single path rather
  than create competing interrupt flows in TTS, UI, or capability code.
- **Alternatives considered**:
  - Let each capability own its own interrupt behavior independently: rejected
    because it would fragment safety behavior and observability.
  - Move interrupt handling into the UI layer: rejected because headless and
    wearable runtime behavior must stay authoritative.

## Decision: Make speech playback genuinely preemptible, not only interrupt-aware at call boundaries

- **Decision**: TTS playback must stop while audio is already playing, not only
  before or after playback begins.
- **Rationale**: The current `TTSEngine.speak()` accepts an interrupt signal but
  still relies on blocking playback behavior, which is not sufficient for the
  Phase 10 requirement of "stop now" assistive control.
- **Alternatives considered**:
  - Keep the current blocking playback and only mark the result as interrupted
    afterward: rejected because it fails the user-facing stop requirement.
  - Stop speech only between queued responses: rejected because long messages
    would remain audible after the user already asked to stop.

## Decision: Reuse `RuntimeRecoveryOutcome` as the primary interrupt observability contract

- **Decision**: Interrupt results should continue using the existing
  `RuntimeRecoveryOutcome` / `RuntimeEventType.SYSTEM` path, extended as needed
  rather than replaced by a separate event family.
- **Rationale**: The project already records `interrupt_signal_type`,
  `completion_status`, and `preemption_latency_ms`, so reusing that path keeps
  Phase 10 incremental and consistent with existing release metrics work.
- **Alternatives considered**:
  - Introduce a brand-new interrupt event model: rejected because it duplicates
    nearby functionality and increases integration churn.
  - Emit only logs without machine-readable outcomes: rejected because latency
    gates and regression assertions need structured data.

## Decision: Use best-effort cancellation semantics for non-reversible work

- **Decision**: When an operation can no longer be fully cancelled, the
  assistant should still stop speech immediately, suppress follow-on work, and
  acknowledge that the underlying action may already be completing.
- **Rationale**: This preserves truthful safety behavior without pretending
  every capability supports a full rollback.
- **Alternatives considered**:
  - Report every accepted interrupt as a full cancellation: rejected because it
    may mislead the user about the true operation state.
  - Ignore interrupts once work nears completion: rejected because speech
    preemption and follow-on suppression still provide real value.

## Decision: Validate interrupt latency against a concrete release target

- **Decision**: Phase 10 validation should enforce a target of interrupting
  audible speech within 500 ms in at least 95% of validation runs, with no
  accepted interrupt case exceeding 1 second.
- **Rationale**: The spec already defines this threshold, and planning needs a
  measurable gate that is strict enough for assistive use without assuming
  unrealistically perfect timing in every run.
- **Alternatives considered**:
  - Record latency without a release target: rejected because it weakens the
    quality gate into passive telemetry.
  - Require every single run to stay under 500 ms: rejected because a p95
    target with a hard 1 second ceiling better fits real runtime variance.

## Decision: Cover interrupt behavior with unit, integration, and smoke validation

- **Decision**: The regression matrix should span vocabulary matching,
  speech-preemption behavior, runtime recovery state, localization integrity,
  and bounded latency checks.
- **Rationale**: Interrupt safety crosses parsing, runtime state transitions,
  prompt localization, TTS behavior, and observability, so no single test layer
  can protect it adequately on its own.
- **Alternatives considered**:
  - Test only runtime interrupt methods directly: rejected because playback and
    observability regressions can still slip through.
  - Rely only on smoke tests: rejected because detailed latency and edge-case
    assertions belong in unit and integration coverage too.
