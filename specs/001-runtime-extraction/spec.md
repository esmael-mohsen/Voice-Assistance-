# Feature Specification: Runtime Extraction

**Feature Branch**: `[001-runtime-extraction]`  
**Created**: 2026-04-16  
**Status**: Draft  
**Input**: User description: "Phase 1 runtime extraction: separate assistant runtime logic from the UI layer, make assistant_worker a UI bridge, define a unified runtime event model, and ensure GUI and console mode use the same runtime behavior."

## Clarifications

### Session 2026-04-16

- Q: Should Phase 1 be strictly behavior-preserving, or may it include broader user-visible changes? -> A: Phase 1 is strictly behavior-preserving, except for fixes required for parity, safety, or stability.
- Q: Should Phase 1 only reroute the existing speech and command layers through the shared runtime, or also refactor them substantively? -> A: Phase 1 only changes speech and command layers as needed to route existing behavior through the shared runtime.
- Q: What should happen after a recoverable runtime failure? -> A: Recoverable failures emit an `error` event, inform the user, then return to `standby`.
- Q: Which failures should force the assistant to `offline`? -> A: Only startup or initialization failures, and explicitly unrecoverable runtime exceptions, force `offline`.
- Q: Is existing first-run voice onboarding part of Phase 1? -> A: Existing first-run voice onboarding is part of Phase 1 and must run through the shared runtime.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consistent Runtime Behavior (Priority: P1)

As a blind or low-vision user, I want the assistant to behave the same way in
debug and non-visual operating modes so I can trust the voice experience while
the product moves toward a headless wearable runtime.

**Why this priority**: Consistent assistant behavior across operating modes is
the main value of this phase and the foundation for all later runtime and
speech work.

**Independent Test**: Start the assistant in both operating modes, wake it,
issue the same supported command, and confirm the same core lifecycle and voice
response behavior occurs in both runs. When no user profile exists, confirm the
same first-run voice onboarding flow is reached through the shared runtime in
both modes.

**Acceptance Scenarios**:

1. **Given** the assistant is started in GUI debug mode, **When** the user
   wakes the assistant and issues a supported command, **Then** the assistant
   completes the same core lifecycle and response flow used in non-visual mode.
2. **Given** the assistant is started in console mode, **When** the user
   performs a normal wake-and-command flow, **Then** the assistant can complete
   the interaction without depending on any visual interface.
3. **Given** no saved user profile exists, **When** the user starts the
   assistant in either operating mode, **Then** the same first-run voice
   onboarding flow runs through the shared runtime rather than a UI-owned path.

---

### User Story 2 - UI as Observer, Not Owner (Priority: P2)

As a local tester or demo operator, I want the debug UI to reflect assistant
runtime activity without owning the runtime behavior so I can monitor the
assistant safely without creating a separate behavior path.

**Why this priority**: The GUI remains valuable for development, but it must no
longer be the authoritative source of runtime logic.

**Independent Test**: Run the assistant with the debug UI and verify that the
UI mirrors the shared lifecycle states and assistant messages instead of
driving a separate runtime flow.

**Acceptance Scenarios**:

1. **Given** the assistant runtime changes state, **When** the debug UI is
   active, **Then** the UI reflects the same named states and runtime messages
   exposed by the shared lifecycle.
2. **Given** the debug UI is unavailable or not in use, **When** the assistant
   runs in non-visual mode, **Then** the assistant can still complete its
   supported voice workflow without losing runtime state.

---

### User Story 3 - Shared Lifecycle for Future Work (Priority: P3)

As a project maintainer, I want one shared runtime lifecycle and event
vocabulary so future speech and capability work can integrate with a single
assistant flow instead of separate GUI and console behaviors.

**Why this priority**: This story reduces future integration risk, but the
immediate user value depends first on consistent assistant behavior.

**Independent Test**: Review the runtime-facing outputs for both operating
modes and confirm the same lifecycle vocabulary can be used to describe
startup, standby, wake, listening, thinking, speaking, error, and offline
behavior.

**Acceptance Scenarios**:

1. **Given** a new observer or integration needs assistant lifecycle updates,
   **When** it consumes runtime activity, **Then** it can rely on one shared
   event vocabulary instead of mode-specific behavior.
2. **Given** a maintainer documents the assistant lifecycle after this phase,
   **When** they compare GUI and non-visual mode, **Then** they can describe
   both using the same runtime states and transitions.

### Edge Cases

- What happens if the visual debug interface is unavailable after the assistant
  runtime has already started?
- How does the assistant behave if a runtime error happens while listening,
  thinking, or speaking in one mode but not the other?
- What happens if repeated or rapid state changes occur during one interaction?
- How is the assistant kept usable when the screen is not present or not being
  watched?
- What happens when startup or initialization fails before the assistant can
  enter normal standby behavior?
- What happens when first-run onboarding is required but the UI layer is not
  active?

## Accessibility & Safety Considerations *(mandatory)*

- **Primary User Impact**: Blind and low-vision users receive a more reliable
  transition toward a headless assistant because the core voice experience is no
  longer tied to a debug-only interface.
- **Audio UX**: Spoken prompts, confirmations, and error messages must stay
  clear, brief, and consistent across operating modes so users do not have to
  learn different behaviors.
- **Non-Visual Operation**: Every primary wake, listen, respond, recover, and
  first-run onboarding flow in this phase must remain usable without looking at
  the debug UI.
- **Failure Handling**: Runtime failures must surface through a clear shared
  state, preserve user awareness, and allow controlled recovery back to
  standby for recoverable failures or controlled shutdown for unrecoverable
  failures. Only startup or initialization failures, and explicitly
  unrecoverable runtime exceptions, may force the assistant offline.
- **Risk Controls**: Existing safeguards around close, stop, and shutdown-like
  voice commands must be preserved so the extraction does not reintroduce unsafe
  or confusing termination behavior.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide one shared assistant runtime lifecycle for
  wake, listening, command handling, speaking, error handling, shutdown
  behavior, and first-run onboarding across operating modes.
- **FR-002**: The system MUST expose runtime state changes through a unified
  event model that includes, at minimum, standby, wake, listening, thinking,
  speaking, error, and offline states.
- **FR-003**: The system MUST allow a visual debug interface to observe and
  present runtime activity without owning or duplicating the core assistant
  behavior.
- **FR-004**: The system MUST ensure that starting the assistant in GUI debug
  mode or in console mode leads to equivalent lifecycle behavior for the same
  supported voice scenario.
- **FR-005**: Users MUST be able to complete the primary wake-and-command flow
  without depending on a visual interface.
- **FR-006**: The system MUST preserve protected handling for close, stop, and
  shutdown-like voice intents during and after the runtime extraction.
- **FR-007**: The system MUST surface runtime failures through the shared event
  model and provide a clear recoverable or offline outcome.
- **FR-008**: The system MUST keep Phase 1 behavior-preserving for end users,
  allowing only changes needed to maintain parity, safety, or runtime
  stability during the extraction.
- **FR-009**: The system MUST limit changes to STT, TTS, parser, dispatcher,
  and resolver behavior to the routing, parity, safety, or stability work
  required to use the shared runtime in this phase.
- **FR-010**: The system MUST handle recoverable runtime failures by emitting
  an `error` event, informing the user, and returning the assistant to
  `standby`.
- **FR-011**: The system MUST reserve the `offline` outcome for startup or
  initialization failures and explicitly unrecoverable runtime exceptions.
- **FR-012**: The system MUST use the shared runtime as the only orchestration
  path for existing first-run voice onboarding so GUI debug mode and console
  mode do not introduce separate onboarding control flows in this phase.

### Operational & Quality Requirements

- **OQ-001**: The affected runtime layers for this feature are `main.py`,
  `core/`, and `ui/`, with `settings/` included only where shared runtime
  behavior depends on configuration.
- **OQ-002**: The runtime lifecycle defined by this feature MUST be the single
  boundary consumed by visual and non-visual observers.
- **OQ-003**: The feature MUST include runtime logging and smoke validation for
  startup, standby, wake, listening, thinking, speaking, error, offline, and
  first-run onboarding behavior in both operating modes.
- **OQ-004**: The shared runtime outputs for this feature MUST preserve spoken
  outcome information together with a shared status and payload that future
  features can build upon.

### Key Entities *(include if feature involves data)*

- **Runtime Session**: A single active assistant lifecycle from startup through
  standby, active interaction, recovery, onboarding, and shutdown.
- **Runtime Event**: A shared lifecycle update that communicates the assistant's
  current state, user-relevant outcome, and any relevant failure context.
- **Runtime Observer**: Any surface that consumes runtime activity, such as the
  debug UI, the console experience used in this phase, or a future headless
  wearable integration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a smoke validation of ten representative wake-and-command runs
  per operating mode, at least 9 out of 10 runs complete the same core
  lifecycle without unexplained mode-specific divergence.
- **SC-002**: The debug UI can reflect all shared runtime states used by the
  assistant without requiring a separate runtime behavior path.
- **SC-003**: Users can complete the primary wake-and-command flow in non-visual
  mode in 100% of acceptance-test runs for this feature.
- **SC-004**: When a recoverable runtime failure is triggered during listening
  or speaking, both operating modes emit a clear error outcome and return to
  `standby` within 5 seconds.
- **SC-005**: When startup, initialization, or an explicitly unrecoverable
  runtime exception fails, both operating modes reach a clear `offline` state
  without first re-entering `standby`.
- **SC-006**: When no saved user profile exists, both operating modes reach the
  same first-run voice onboarding flow without requiring a separate UI-owned
  runtime path.

## Assumptions

- The debug UI remains a local development and demonstration surface during this
  phase and is not the target runtime for the final glasses experience.
- Supported commands and spoken responses keep their current user-facing
  behavior unless a change is required to preserve consistency across modes.
- Existing safety behavior around protected stop and close flows remains in
  scope and must continue to work after the runtime extraction.
- Later phases will build speech-provider abstractions and capability changes on
  top of the shared runtime lifecycle established here.
- Speech abstraction, provider replacement, and command-model redesign remain
  out of scope for this phase unless a minimal routing change is required to
  preserve shared runtime behavior.
