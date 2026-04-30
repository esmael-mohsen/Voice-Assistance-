# Research: Speech Abstraction and SpeakKit Adapter

## Decision: Add a dedicated `core/speech/` adapter layer

- **Decision**: Introduce provider-facing modules under `core/speech/` with
  explicit interfaces for wake detection, speech input, and speech output.
- **Rationale**: This satisfies constitution requirements for replaceable
  provider boundaries while avoiding a rewrite of runtime or UI layers.
- **Alternatives considered**:
  - Keep provider logic in `core/stt.py` and `tts/tts_engine.py` directly:
    rejected because it hard-wires providers and complicates fallback policy.
  - Place speech adapters in `ui/`: rejected because runtime ownership must
    remain outside UI.

## Decision: Preserve runtime authority in `core/assistant_runtime.py`

- **Decision**: Keep provider selection, fallback orchestration, and lifecycle
  transitions controlled by the shared runtime service.
- **Rationale**: Runtime control already exists in a mode-neutral service; this
  feature extends that path without reintroducing UI-owned orchestration.
- **Alternatives considered**:
  - Implement provider switching in UI worker: rejected because it violates the
    runtime/UI separation principle.
  - Split separate runtime loops per provider: rejected due to duplication and
    parity risk.

## Decision: Use persisted provider selection with restart-only switch

- **Decision**: Persist provider mode in user profile; apply switch requests on
  next restart when requested during active sessions.
- **Rationale**: This matches clarifications and minimizes transition risk in
  assistive usage where predictable behavior is critical.
- **Alternatives considered**:
  - Live hot-swap provider during active session: rejected due to higher
    stability risk and harder recovery semantics.
  - Session-only provider selection: rejected because it increases operator
    friction and weakens repeatability.

## Decision: Enforce directional fallback policy

- **Decision**: Allow recoverable fallback from active SpeakKit mode to legacy
  mode; prohibit automatic fallback from legacy mode to SpeakKit.
- **Rationale**: Legacy path is current stable baseline; this directional rule
  reduces surprising behavior while still enabling SpeakKit degradation.
- **Alternatives considered**:
  - Bidirectional automatic cross-provider fallback: rejected because legacy to
    SpeakKit auto-promotion is less predictable and riskier.
  - No cross-provider fallback: rejected because it would degrade reliability
    for SpeakKit sessions.

## Decision: Handle startup provider unavailability as temporary degradation

- **Decision**: If persisted provider is unavailable at startup, use legacy for
  the current session, keep saved provider unchanged, and emit degraded-mode
  notification.
- **Rationale**: Preserves user intent and usability, while making temporary
  degradation explicit.
- **Alternatives considered**:
  - Overwrite saved provider to legacy automatically: rejected because it
    silently changes user preference.
  - Fail startup immediately/offline: rejected because it sacrifices usability
    when a safe degraded path exists.

## Decision: Transition offline when both providers are unavailable

- **Decision**: If both primary and fallback providers are unavailable, move to
  offline and require manual restart.
- **Rationale**: Prevents unstable retry loops and ensures a clear operator
  recovery path.
- **Alternatives considered**:
  - Infinite retry loop in standby: rejected due to poor reliability and user
    confusion.
  - Continue silently without speech I/O: rejected because non-visual users
    would receive no actionable feedback.

## Decision: Extend observer payloads with provider context

- **Decision**: Keep existing runtime event types while adding provider-aware
  fields in `config`/`error` payloads for active provider, fallback source, and
  degraded-mode reason.
- **Rationale**: Preserves compatibility with existing observer paths while
  improving observability required by constitution quality gates.
- **Alternatives considered**:
  - Introduce brand-new event types for providers: rejected to avoid avoidable
    observer churn.
  - Log-only provider state with no event payload fields: rejected because
    automated validation would be weaker.

## Decision: Validate with layered tests and deterministic smoke checks

- **Decision**: Add unit tests for provider resolver and fallback logic,
  integration tests for startup degradation and directional fallback, and smoke
  validation for parity and offline transitions.
- **Rationale**: This directly maps to measurable success criteria and reduces
  regression risk in a safety-sensitive runtime.
- **Alternatives considered**:
  - Manual validation only: rejected due to low repeatability.
  - Hardware-only validation before automated tests: rejected because it slows
    iteration and weakens CI-style confidence.
