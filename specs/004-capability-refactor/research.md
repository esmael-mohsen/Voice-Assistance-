# Research: Capability Refactor

## Decision: Introduce a registry-backed `CapabilityHandler` contract

- **Decision**: Replace the resolver's direct dependency on shared free
  functions in `controllers.mock_controllers` with a registry-backed capability
  contract. Each capability will register metadata plus a handler that exposes
  `start()`, `stop()`, `execute()`, and `get_status()` as applicable.
- **Rationale**: The current free-function map in `core.resolver.py` is simple
  but does not scale to per-capability timeout policy, explicit fallback rules,
  or status snapshots. A registry keeps command routing incremental while
  removing the shared mock file as the long-term bottleneck.
- **Alternatives considered**:
  - Continue mapping intents directly to new module functions: rejected because
    timeout, fallback, and observability rules would be duplicated per intent.
  - Require every controller to inherit from one concrete base class: rejected
    because a lighter contract plus registry is easier to adopt incrementally.

## Decision: Preserve the current command layer and map intents to capability actions

- **Decision**: Keep the bilingual parser and dispatcher surface from feature
  `003-command-layer-hardening`, but change resolver internals so supported
  capability intents map to `(capability_id, action)` pairs rather than direct
  mock functions.
- **Rationale**: The clarified spec explicitly forbids new user-facing
  commands. Reusing the existing command layer keeps GUI and console behavior
  stable while allowing capability routing to evolve underneath it.
- **Alternatives considered**:
  - Redesign the command vocabulary during capability extraction: rejected
    because it mixes user-facing risk with controller refactoring.
  - Bypass resolver and let runtime call controllers directly: rejected because
    resolver already owns parameter inference and follow-up context.

## Decision: Migrate obstacle detection first behind a dedicated obstacle adapter

- **Decision**: Treat obstacle detection as the first migrated real capability
  and place it behind an explicit obstacle adapter boundary with health checks,
  start or stop support, and synchronous observation reads for status or
  execution results.
- **Rationale**: Obstacle detection is high-value, safety-sensitive, and easier
  to validate end-to-end than multi-step OCR or face/emotion flows. Its
  behavior can be expressed cleanly as machine-readable state plus brief spoken
  guidance.
- **Alternatives considered**:
  - Migrate OCR first: rejected because OCR adds text-content variability and a
    wider payload surface before the capability contract is proven.
  - Migrate system status first: rejected because it is useful scaffolding but
    does not prove a sensor-backed capability boundary.

## Decision: Enforce capability timeouts in a shared runner at the controller boundary

- **Decision**: Apply capability-specific timeout policies through a shared
  runner that wraps handler calls and returns explicit timeout failures with
  bounded recovery behavior. Obstacle actions should target 3.0 seconds or
  less on an available backend, and no capability may exceed the clarified hard
  maximum of 10.0 seconds.
- **Rationale**: Timeout enforcement must be centralized so handlers cannot
  block the runtime indefinitely and so failure telemetry remains consistent.
  A shared runner also keeps timeout logic out of UI code and out of each
  controller implementation.
- **Alternatives considered**:
  - Let each capability implement its own ad hoc timers: rejected because it
    creates inconsistent failure behavior and hard-to-test recovery paths.
  - Use platform-specific signal timeouts: rejected because Windows support is
    weaker and the project runs primarily on Windows.

## Decision: Keep fallback explicit and limited to unmigrated or test-only capabilities

- **Decision**: Wrap legacy mock behavior in explicit fallback handlers or
  registry entries for capabilities that are not yet migrated or for test-only
  scenarios. Migrated real capabilities, starting with obstacle detection, must
  return safe explicit failures instead of silently invoking fallback when
  their real backend fails.
- **Rationale**: This matches the spec clarification and keeps production
  operator trust intact. It also makes migration state visible in logs, tests,
  and runtime status rather than hidden behind legacy behavior.
- **Alternatives considered**:
  - Automatically fallback whenever a migrated capability fails: rejected
    because it masks real failures and makes safety behavior ambiguous.
  - Remove fallback immediately for every capability: rejected because the
    clarified minimum scope requires shared scaffolding for the remaining
    capabilities.

## Decision: Store machine state in payloads and snapshots, not in spoken strings

- **Decision**: Capability handlers will return structured payloads and status
  snapshots as the system of record, while spoken strings remain a user-facing
  rendering generated at the capability edge.
- **Rationale**: The Phase 4 notes explicitly reject "spoken strings as state"
  patterns. Machine state must stay machine-readable so resolver, runtime, and
  downstream tests can reason about capability health and output safely.
- **Alternatives considered**:
  - Continue inferring state from return strings or localized phrases: rejected
    because localization changes would also change program behavior.
  - Push speech generation entirely into runtime: rejected because each
    capability still needs to provide concise user guidance tailored to its
    result.

## Decision: Validate the refactor with layered contract, runtime, and smoke coverage

- **Decision**: Add unit tests for capability contracts, registry behavior,
  timeout handling, and obstacle controller logic; integration tests for
  resolver, dispatcher, and runtime parity; and smoke scenarios for console and
  GUI-assisted flows, including baseline timing capture.
- **Rationale**: Capability extraction changes runtime-affecting boundaries and
  must satisfy the constitution's test, observability, and latency rules.
  Layered coverage is needed to prove both contract stability and operator-
  visible behavior.
- **Alternatives considered**:
  - Manual capability checks only: rejected because they cannot prove fallback
    restrictions or timeout safety.
  - Unit tests only: rejected because mode parity and runtime recovery need
    higher-level validation.
