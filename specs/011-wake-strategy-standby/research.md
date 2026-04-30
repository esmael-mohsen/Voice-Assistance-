# Research: Wake Strategy and Low-Power Standby

## Decision: Keep wake policy runtime-owned and evaluate it once per standby entry

- **Decision**: Wake-mode selection should remain owned by the runtime and
  provider-resolution boundary, with a concrete wake policy chosen each time
  the assistant enters standby.
- **Rationale**: The current runtime already resolves provider and connectivity
  state before entering standby. Reusing that boundary keeps Phase 11
  incremental and prevents wake behavior from fragmenting across UI, settings,
  or provider-specific code.
- **Alternatives considered**:
  - Let each wake provider decide policy independently: rejected because it
    would create inconsistent production vs development behavior.
  - Move wake selection into settings-only logic: rejected because settings
    should persist policy, not execute runtime decisions.

## Decision: Production-like standby must not rely on always-on free-form STT

- **Decision**: When keyword or hardware-trigger wake is permitted, standby
  should wait on that wake boundary rather than continuously running
  `listen_any()` for open-ended speech.
- **Rationale**: The Phase 11 goal is lower-power, more predictable wearable
  standby. The current runtime still listens through STT while idle, which does
  not honor the configured wake modes in a meaningful way.
- **Alternatives considered**:
  - Keep the current always-on STT loop and label it as low power: rejected
    because it does not materially change standby cost or false-wake exposure.
  - Disable standby listening entirely unless hardware exists: rejected because
    keyword wake remains an intended supported path.

## Decision: STT-based wake remains a development-only fallback

- **Decision**: STT wake is allowed only when the configuration explicitly
  enables the development fallback path; production-like configurations must
  reject STT wake even if the phrase matches.
- **Rationale**: Developers still need a practical fallback on non-final
  hardware, but production safety requires a hard separation so open-ended STT
  does not silently become the effective wearable wake path.
- **Alternatives considered**:
  - Allow STT wake whenever other wake sources fail: rejected because it
    weakens the production guardrail and hides degraded hardware states.
  - Remove STT wake entirely: rejected because it would slow testing and early
    validation on incomplete hardware setups.

## Decision: Use safe degraded standby when no permitted wake source is available

- **Decision**: If the current configuration has no usable permitted wake
  source, the runtime should enter safe standby, emit one degraded
  notification, and wait for configuration or hardware recovery.
- **Rationale**: This preserves truthful, non-visual feedback without silently
  enabling a forbidden fallback or bouncing the whole assistant offline.
- **Alternatives considered**:
  - Fail startup immediately: rejected because it removes the chance to recover
    cleanly during the session.
  - Fall back to manual or STT wake automatically: rejected because it hides a
    policy violation behind convenience behavior.

## Decision: Competing permitted wake signals use first-valid-wins arbitration

- **Decision**: When more than one permitted wake source triggers close
  together, the first valid accepted signal starts the wake cycle and later
  competing signals are ignored until that cycle completes.
- **Rationale**: This is the simplest deterministic rule for a wearable
  assistant and avoids duplicate wake transitions or double prompts.
- **Alternatives considered**:
  - Fixed source priority: rejected because it adds complexity without a clear
    user benefit for this phase.
  - Single-source-only configurations: rejected because the spec explicitly
    allows more than one permitted wake source to exist.

## Decision: Reuse structured runtime outcomes and release metrics for wake observability

- **Decision**: Wake-policy behavior should publish machine-readable wake-mode,
  acceptance, rejection, degraded-reason, and latency data through the current
  runtime event and release-metrics paths rather than a separate observability
  stack.
- **Rationale**: The project already records wake-to-listen and other runtime
  timings, so Phase 11 should extend those paths instead of creating a parallel
  telemetry model.
- **Alternatives considered**:
  - Emit only plain logs: rejected because release validation and smoke checks
    need structured assertions.
  - Create a brand-new wake telemetry subsystem: rejected because it adds
    unnecessary architectural churn.

## Decision: Standardize wake baselines around a 10-cycle light-load scenario

- **Decision**: The wake baseline scenario will use 10 sequential wake cycles
  on an otherwise idle assistant session with stable provider availability and
  no concurrent long-running capability work.
- **Rationale**: This is concrete enough for repeatable release checks and
  aligns directly with the clarified success criteria.
- **Alternatives considered**:
  - Ad hoc manual timing checks: rejected because they are not reproducible.
  - Heavy-load-only validation: rejected because Phase 11 is primarily about
    safe standby correctness before performance under broader contention.

## Decision: Cover wake policy with unit, integration, and smoke validation

- **Decision**: Validation must span pure policy selection, runtime standby
  execution, headless parity, degraded standby handling, and latency baselines.
- **Rationale**: Wake behavior crosses configuration, provider selection,
  runtime orchestration, and release evidence, so no single test layer is
  enough.
- **Alternatives considered**:
  - Unit tests only: rejected because runtime state transitions and headless
    parity would still be underprotected.
  - Smoke tests only: rejected because wake-policy edge cases and rejection
    behavior need deterministic assertions.
