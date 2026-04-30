# Research: Runtime Extraction

## Decision: Add `core/assistant_runtime.py` as the shared runtime service

- **Decision**: Create `core/assistant_runtime.py` as the single runtime
  authority for lifecycle control, wake handling, command dispatch, recoverable
  failure behavior, and first-run onboarding.
- **Rationale**: The current `AssistantWorker` mixes UI concerns with runtime
  ownership. A dedicated runtime module makes console and GUI parity possible
  without a rewrite and aligns directly with the project constitution.
- **Alternatives considered**:
  - Keep the runtime loop inside `ui/assistant_worker.py`: rejected because it
    leaves `ui/` as the long-term runtime owner.
  - Use `core/runtime.py`: rejected because `assistant_runtime.py` is more
    explicit and easier to understand during incremental migration.

## Decision: Preserve current speech and command behavior in Phase 1

- **Decision**: Treat `VoiceListener`, `TTSEngine`, `dispatch`, and
  `WakeWordDetector` as existing runtime dependencies that are rerouted through
  the new runtime service without redesigning their contracts in this phase.
- **Rationale**: The clarified spec limits Phase 1 to behavior-preserving
  extraction. This reduces risk and keeps speech abstraction and command-layer
  hardening in their planned later phases.
- **Alternatives considered**:
  - Start introducing speech interfaces now: rejected because it expands Phase
    1 into Phase 2 work.
  - Redesign parser or resolver outputs now: rejected because it mixes runtime
    extraction with command hardening.

## Decision: Standardize on a mode-neutral runtime event contract

- **Decision**: Define a runtime event contract that preserves the current
  observer-facing categories (`status`, `system`, `config`, `user`,
  `assistant`, `error`) while documenting canonical lifecycle states and
  payload expectations.
- **Rationale**: The GUI already depends on these event categories. Keeping
  them stable minimizes churn while still allowing the runtime to become UI
  independent.
- **Alternatives considered**:
  - Expose `Queue` objects from the core runtime: rejected because it keeps
    the contract tied to UI implementation details.
  - Invent a completely new event schema: rejected because it creates
    avoidable migration work during a parity-focused phase.

## Decision: Make console mode an observer of the same runtime service

- **Decision**: Replace the direct `while True -> listen_command -> dispatch`
  loop in `main.py --console` with a console observer that starts the shared
  runtime and consumes its events.
- **Rationale**: The feature’s main success condition is that GUI and console
  mode run on the same runtime layer. A console observer preserves the mode
  while removing divergent control flow.
- **Alternatives considered**:
  - Keep the current console loop and only extract the GUI path: rejected
    because it fails the feature exit criteria.
  - Create a second runtime implementation for console mode: rejected because
    it preserves divergence instead of eliminating it.

## Decision: Keep first-run voice onboarding inside the shared runtime

- **Decision**: Treat the current voice onboarding flow as part of the shared
  runtime lifecycle and route it through the same runtime service used for GUI
  and console mode.
- **Rationale**: First-run onboarding is already part of the real runtime path
  in `AssistantWorker`. Leaving it behind would strand a high-value runtime
  flow in the UI bridge and break parity for new users.
- **Alternatives considered**:
  - Leave onboarding in `AssistantWorker`: rejected because it violates the
    shared-runtime goal.
  - Defer onboarding parity to a later phase: rejected because the clarified
    spec explicitly includes it in scope.

## Decision: Use explicit recoverable and unrecoverable failure transitions

- **Decision**: Recoverable runtime failures emit `error`, inform the user, and
  return to `standby`. Only startup or initialization failures, and explicitly
  unrecoverable runtime exceptions, force `offline`.
- **Rationale**: This gives blind users a predictable recovery path and creates
  clear acceptance tests for runtime-state handling.
- **Alternatives considered**:
  - Resume directly to `listening` after failure: rejected because it can feel
    abrupt and harder to reason about.
  - Move all exceptions to `offline`: rejected because it is too harsh for
    transient or recoverable errors.

## Decision: Add focused runtime tests and smoke validation in this phase

- **Decision**: Add pytest coverage around runtime state transitions and
  observer notifications, plus repeatable smoke validation for GUI and console
  mode with and without an existing profile.
- **Rationale**: The constitution requires tests, observability, and real
  execution checks for runtime-affecting work.
- **Alternatives considered**:
  - Manual validation only: rejected because it is not strong enough for a
    safety-sensitive runtime refactor.
  - Full end-to-end hardware testing now: rejected because it belongs to later
    readiness phases.
